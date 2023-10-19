import time

import stripe
from django.conf import settings
from django.db import transaction as atomic_transaction
from django.apps import apps


def stripe_create_account(vendor, country):
    """ Connect a vendor to a stripe account
    """
    if not vendor.stripe_id and vendor.user.is_active:
        account = stripe.Account.create(
            country=country,
            type="custom",
            business_type="individual",
            requested_capabilities=["card_payments", "transfers"],
            email=vendor.user.email,
            individual={"email": vendor.user.email},
            settings={
                "payouts": {
                    "debit_negative_balances": True,
                    "schedule": {"interval": "manual"},
                }
            },
        )
        stripe_id = account.get("id")
        vendor.stripe_id = stripe_id
        vendor.stripe_account = account
        vendor.stripe_uptodate = True
        vendor.save()
        return account
    return None


def retrieve_stripe_account(vendor):
    if vendor.stripe_id:
        account = stripe.Account.retrieve(vendor.stripe_id)
        return account
    return None


def update_stripe_account(vendor, metatdata):
    """
    Meta data should be a dict with updated values for the Stripe account ( Vendor )
    """
    if not vendor.stripe_id:
        account = stripe.Account.modify(vendor.stripe_id, metatdata=metatdata)
        return account
    return None


def stripe_retrieve_and_update_stripe_account(vendor):
    account = retrieve_stripe_account(vendor)
    if account:
        vendor.stripe_account = account
        vendor.save()
        return account
    else:
        return None


def _application_fee_amount(amount):
    application_fee_amount = int(int(amount) / 100 * 10)
    return str(application_fee_amount)


def stripe_checkout_session_create(
    product, quantity, amount, user, success_url, cancel_url
):
    line_item = product.to_line_item
    str_amount = str(amount) + "00"
    str_application_fee = _application_fee_amount(str_amount)
    line_item.update(
        {"amount": str_amount, "quantity": quantity, "name": product.title}
    )
    session = stripe.checkout.Session.create(
        customer_email=user.email,
        payment_method_types=["card", "ideal"],
        line_items=[line_item],
        mode="payment",
        payment_intent_data={
            "application_fee_amount": str_application_fee,
            "transfer_data": {"destination": product.vendor.stripe_id},
            "metadata": product.to_dict,
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session


def stripe_accept_tos(vendor):
    stripe.Account.modify(
        vendor.stripe_id, tos_acceptance={"date": int(time.time()), "ip": "8.8.8.8"}
    )


def stripe_link_account(vendor_id, failure_url, succes_url, stripe_type):
    account_link = stripe.AccountLink.create(
        account=vendor_id,
        failure_url=failure_url,
        success_url=succes_url,
        type=stripe_type,
    )
    return account_link


def stripe_account_company_or_individual(vendor_id):
    """
    Scenario 1
    User has no company or individual type

    Scenario 2
    User has company or individual type and want to update data

    """
    account = stripe.Account.retrieve(vendor_id)

    # Catch Scenario 1
    if not account.get("individual") or not account.get("company"):
        return "custom_account_verification"

    # Catch Scenario 2
    if account.get("individual") or account.get("company"):
        return "custom_account_update"


def stripe_retrieve_account(vendor_id):
    account = stripe.Account.retrieve(vendor_id)
    if account:
        return account
    else:
        return None


def stripe_create_bank_account(
    vendor_id,
    country,
    currency,
    account_number,
    bank_account_obj="bank_account",
    routing_number=None,
):
    bank_account = stripe.Account.create_external_account(
        id=vendor_id,
        external_account={
            "object": bank_account_obj,
            "country": country,
            "currency": currency,
            "account_number": account_number,
            "routing_number": routing_number,
            "default_for_currency": True,
        },
    )
    if bank_account and bank_account.get("status") == "new":
        return (True, "Success")
    return (False, bank_account)


def stripe_retrieve_first_bank_account(vendor_id):
    account = stripe_retrieve_account(vendor_id)
    if (
        account
        and account.get("external_accounts")
        and account.get("external_accounts").get("data")
    ):
        bank_account = account.get("external_accounts").get("data")[0]
    else:
        bank_account = None
    return bank_account


def stripe_update_bank_account(
    vendor_id,
    country,
    currency,
    account_number,
    bank_account_obj="bank_account",
    routing_number=None,
):
    account = stripe_retrieve_account(vendor_id)
    if account and account.get("external_accounts"):
        # Get first bank account
        bank_account = stripe.Account.modify_external_account(
            id=vendor_id,
            external_account={
                "object": bank_account_obj,
                "country": country,
                "currency": currency,
                "account_number": account_number,
                "routing_number": routing_number,
            },
        )
        if bank_account and bank_account.get("status") == "new":
            return (True, "Success")
    return (False, "Something went wrong it looks like you dont have a bank account")


def stripe_retrieve_country_spec(country):
    retrieve_country = stripe.CountrySpec.retrieve(country)
    supported_currencies = [{"value": None, "label": "----------"}]
    for country in retrieve_country.get("supported_bank_account_currencies"):
        supported_currencies.append({"value": country, "label": country})
    response = {
        "country_id": retrieve_country.get("id"),
        "object": retrieve_country.get("object"),
        "default_currency": retrieve_country.get("default_crrency"),
        "supported_currencies": supported_currencies,
    }
    if response:
        return response
    else:
        return (False, "Something went wrong.")


def stripe_delete_bank_account(vendor_id, bank_id):
    response = stripe.Account.delete_external_account(vendor_id, bank_id)
    if response.get("deleted"):
        return (True, "Deleleted old bank account")
    else:
        return (False, "Something went wrong")


def stripe_retrieve_balance(vendor_id):
    balance = stripe.Balance.retrieve(stripe_account=vendor_id)
    if balance:
        return {
            "amount": balance.get("available")[0].get("amount"),
            "currency": balance.get("available")[0].get("currency"),
        }
    return None


def stripe_charge_create(
    amount, application_fee_amount, vendor_id, description=None, source=None
):
    charge = stripe.Charge.create(
        amount=amount,
        application_fee_amount=application_fee_amount,
        on_behalf_of=vendor_id,
        currency="eur",
        source=source,
        description=description,
        destination=vendor_id,
    )
    return charge


def stripe_list_all_transfers(limit=100, destination=None):
    transfers = stripe.Transfer.list(limit=limit, destination=destination)
    return transfers


def stripe_create_payout(vendor, amount, currency):
    # Request payout for connected account ( Seller )
    Transaction = apps.get_model("marketplace", "Transaction")
    Payout = apps.get_model("marketplace", "Payout")
    stripe_amount = stripe_convert_application_to_stripe_amount(amount)
    fee = stripe_convert_stripe_to_application_fee(stripe_amount)
    if stripe_retrieve_first_bank_account(vendor.stripe_id):
        currency = stripe_retrieve_first_bank_account(vendor.stripe_id).get("currency")
    else:
        currency = None
    if currency:
        response = stripe.Payout.create(
            amount=stripe_amount, currency=currency, stripe_account=vendor.stripe_id
        )
    else:
        return {
            "status": "failed",
            "message": "Vendor first needs to add approved bank account",
        }

    with atomic_transaction.atomic():
        payout = Payout.objects.create(
            currency=currency,
            stripe_id=response.get("id"),
            method="stripe_payout",
            fee=fee,
            amount=amount,
            status=Payout.OMW
            if response.get("failure_code") is not (None or "null")
            else Payout.FAILED,
            data=response,
        )
        Transaction.objects.create(vendor=vendor, payout=payout, type="payout")
    return response


def stripe_cancel_payout(stripe_payout_id):
    response = stripe.Payout.cancel(stripe_payout_id,)
    return response


def stripe_convert_application_to_stripe_amount(amount):
    return float(round(amount * 100, 0))


def stripe_convert_stripe_to_application_fee(amount):
    return float(float(amount) / settings.FEE_PERCENTAGE / 100)


def stripe_convert_stripe_to_application_amount(amount):
    return float(amount / 100)


def stripe_get_account_link_type(vendor):
    account = retrieve_stripe_account(vendor)
    if account:
        if account.get("email"):
            return "account_update"
        else:
            return "account_onboarding"
    return "account_onboarding"


def stripe_connected_ecommerce(vendor):
    """
    Check if the connected user can use ecommerce
    """
    account = retrieve_stripe_account(vendor)
    # account.get("payouts_enabled") and account.get("charges_enabled") use later
    if account:
        if (
            account.get("payouts_enabled")
        ):
            return True
        return False
    return False
