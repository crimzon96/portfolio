import logging

from django.db.models import Sum
from snap.apps.marketplace.stripe import (
    stripe_create_payout,
    stripe_retrieve_balance,
    stripe_convert_application_to_stripe_amount,
    stripe_cancel_payout,
)
from snap.apps.marketplace.models import Order, Payment

logger = logging.getLogger(__name__)


class VendorBalanceWithdraw:
    """
    Vendor requesting a payout.

    Check if the balance of the requested vendor is enought to withdraw the money that he wants.
    I should check this on both client and server side.

    Scenario 1
    Vendor has enough balance to send to bank and the application and stripe verifies that it is possible
    """

    def __init__(self, user):
        self.user = user
        self.vendor = user.vendor

    def verify_application(self, amount):
        # Verify if the vendor can legit withdraw the amount that is requested.
        available_payout = (
            Payment.objects.filter(
                order__status=Order.COMPLETED,
                status=Payment.SUCCESS,
                transaction__vendor=self.vendor,
            )
            .aggregate(amount=Sum("amount"))
            .get("amount")
        )
        # print(amount)
        # print(available_payout)
        if not available_payout:
            return {"status": "unapproved", "message": "Account has insufficient funds"}
        if amount <= float(available_payout):
            return {"status": "approved", "message": "Payout approved"}
        elif amount >= float(available_payout):
            return {"status": "unapproved", "message": "Account has insufficient funds"}
        else:
            return {"status": "error", "message": "Something went wrong"}

    def verify_stripe(self, amount):
        balance = stripe_retrieve_balance(self.vendor.stripe_id)
        stripe_amount = stripe_convert_application_to_stripe_amount(amount)
        if balance and stripe_amount <= balance.get("amount"):
            return {"status": "approved", "message": "Payout approved"}
        elif balance and stripe_amount >= stripe_amount:
            return {"status": "unapproved", "message": "Account has insufficient funds"}
        else:
            return {"status": "error", "message": "Something went wrong"}

    def create_payout(self, amount):
        float_amount = float(amount)
        verify_application = self.verify_application(float_amount)
        verify_stripe = self.verify_stripe(float_amount)
        self.verify_application(float_amount)
        if (
            verify_application
            and verify_application.get("status") == "approved"
            and verify_stripe
            and verify_stripe.get("status") == "approved"
        ):
            response = stripe_create_payout(self.vendor, float_amount)
            try:
                if (
                    response
                    and response.get("status") != "failed"
                    and stripe_convert_application_to_stripe_amount(float_amount)
                    == response.get("amount")
                ):
                    return response
                else:
                    stripe_cancel_payout(response.get("id"))
                    return response
            except Exception as e:
                print(e)
                pass
        elif (
            verify_application.get("status") == "unapproved"
            or verify_stripe.get("status") == "unapproved"
        ):
            return {"status": "unapproved", "message": "Account has insufficient funds"}
        elif (
            verify_application.get("status") == "error"
            or verify_stripe.get("status") == "error"
        ):
            return {"status": "error", "message": "Something went wrong"}
        else:
            return {"status": "error", "message": "Something went wrong"}

class BasketVendor:
    """
    Get basket of requested user.

    A basket is always unique to one requested user and vendor!!

    Check if current basket of requested user is already made with a different vendor.

    Scenario 1
    User has no basket:

    When the requested user has no basket the basket get created with the vendor id of the product.

    Scenario 2
    User has basket and wants to buy other product of the same vendor:

    When the requested user has a basket with a vendor and wants to add other product.
    The basked get cleared and add new product.

    Scenario 3
    User has basket with already a product of a vendor and wants to add a product of another vendor:


    Scenario 4
    Django oscar creates a basket for every user should counter this in the future but for now.
    Add the first vendor to the basket

    When the requested user has a basket filled with a product of a vendor and wants to buy another vendors product.
    It should "close" the basket of the current vendor. We can later use this for analytics.
    And make a new basket with the new vendors product in it.
    """

    def __init__(self, user, vendor, product):
        self.vendor = vendor
        self.user = user
        self.product = product

    def create_new_basket(self):
        if self.user.get_user_basket is None:
            basket = Basket.objects.create(owner=self.user, vendor=self.vendor)
            return basket

    def validate_product_vendor(self, basket):
        if basket.lines.exists():
            line = basket.lines.first()
            if line and line.product.vendor != self.vendor:
                logger.info(
                    "The vendor of the product is not the same as the vendor in de basket"
                )
                return False
            return True

    def remove_current_product(self, basket):
        """
        The requested user requested a other product of the same vendor.
        This function should remove the current product.
        """
        if basket.lines.exists():
            line = basket.lines.first()
            if line and line.product != self.product:
                line.delete()
                logger.info("Delete current product of the same vendor from the basket")
                return True
            return False

    def change_current_basket_status(self, basket):
        # Change current basket status to Other vendor
        basket.status = Basket.OTHER_VENDOR
        basket.save(update_fields=["status"])
        self.create_new_basket()

    def get_or_create_new_basket_vendor(self):
        basket = self.user.get_user_basket
        # Catch Scenario 1 when the user has no basket
        if not basket:
            basket = self.create_new_basket()
            logger.info("Create a new basket")
            return basket

        # Catch Scenario 2
        elif (
            self.vendor == self.product.vendor
            and basket.lines.exists()
            and self.product != basket.lines.first().product
        ):
            self.remove_current_product(basket)
            logger.info("Remove current product from basket")

        # Catch Scenario 3
        elif self.vendor != self.product.vendor and basket.lines.exists():
            self.change_current_basket_status(basket)
            logger.info(
                "Put status from basket to other vendor and create a new basket"
            )

        # Catch Scenario 4
        elif not basket.vendor:
            basket.vendor = self.vendor
            basket.save(update_fields=["vendor"])

        return basket

class AddProductToBasket(APIView):
    """
    What to post:
    {
        "vendor_id": "8",
        "product_id": "1"
    }
    """

    def post(self, request, pk=None, format=None):
        if self.request.user.is_authenticated:
            vendor = Vendor.objects.get(id=request.data.get("vendor_id"))
            product = Product.objects.get(id=request.data.get("product_id"))
            quantity = request.data.get("quantity")
            amount = request.data.get("amount")
            basket_vendor = BasketVendor(
                user=self.request.user, vendor=vendor, product=product
            )
            basket = basket_vendor.get_or_create_new_basket_vendor()
            if not basket.lines.exists():
                basket.add_product(
                    product=product, stockrecord=product.stockrecord, quantity=quantity
                )
            if basket.lines.exists():

                session = stripe_checkout_session_create(
                    product=product,
                    quantity=quantity,
                    amount=amount,
                    user=self.request.user,
                    success_url=settings.BASE_URL,
                    cancel_url=settings.BASE_URL,
                )
                data = {
                    "stripe_account_id": vendor.stripe_id,
                    "checkout_session_id": session.get("id"),
                }
                return Response(data, status=200)
            return Response("Something went wrong", status=400)
        else:
            pass
