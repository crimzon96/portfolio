class StandardResultsSetPagination(PageNumberPagination):
    page_size = 2
    page_size_query_param = "page_size"
    max_page_size = 2

    def get_paginated_response(self, data):
        def _num_pages(pages):
            num_pages = []
            for num in range(1, pages + 1):
                num_pages.append(num)
            return num_pages

        return Response(
            {
                "links": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "count": self.page.paginator.count,
                "num_pages": _num_pages(self.page.paginator.num_pages),
                "results": data,
            }
        )

class ReviewSectionApiView(viewsets.ModelViewSet):
    queryset = ProductReview.objects.all()
    pagination_class = StandardResultsSetPagination
    serializer_class = serializers.ProductReviewSerializer

    @action(detail=False, methods=["get"])
    def product_review(self, request, pk=0):
        if request.data.get("product_id"):
            pk = request.data.get("product_id")
        recent_users = ProductReview.objects.filter(product__id=pk)

        page = self.paginate_queryset(recent_users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(recent_users, many=True)
        return Response(serializer.data)


class ProductApiView(viewsets.ModelViewSet):
    serializer_class = serializers.ProductSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = "slug"

    def get_queryset(self):
        queryset = Product.objects.select_related("vendor")
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset

    @action(detail=False, methods=["get"])
    def vendor_products(self, request, pk=None):
        products = Product.objects.filter(vendor=self.request.user.vendor).order_by(
            "stockrecords__price_excl_tax"
        )
        serializer = serializers.ProductSerializer(
            products, context={"request": request}, many=True
        )
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def vendor_products_search(self, request, pk=None):
        search = request.data.get("search")
        price = request.data.get("price")
        # reviews = request.data.get("reviews")
        status = request.data.get("status")
        queryset = Product.objects.order_by("stockrecords__price_excl_tax")
        if search:
            queryset = Product.objects.filter(
                Q(title__istartswith=search) | Q(description__istartswith=search)
            )
        if price == "high_low":
            queryset = queryset.order_by("-stockrecords__price_excl_tax")
        if price == "low_high":
            queryset = queryset.order_by("stockrecords__price_excl_tax")
        if status == "draft":
            queryset = queryset.filter(is_public=False)
        if status == "live":
            queryset = queryset.filter(is_public=True)
        serializer = serializers.ProductSerializer(
            queryset, context={"request": request}, many=True
        )
        return Response(serializer.data)

class IncomeTrackerApiView(APIView):
    def _line_chart(self, label, values, category_count):
        color_sets = [
            ("rgba(89,124,255,1)", "rgba(89,124,255,0.2)", "black"),
            ("rgba(113,201,77,1)", "rgba(113,201,77,0.2)", "black"),
            ("rgba(89,124,255,1)", "rgba(89,124,255,0.2)", "black"),
            ("#ff5959", "black", "red"),
            ("#71c94d", "black", "purple"),
            ("#e8c067", "black", "yellow"),
            ("#24d2e2", "black", "orange"),
            ("#6d6f71", "black", "gray"),
        ]
        primary, secondary, tertiary = color_sets[int(category_count)]
        dataset = {
            "label": label,
            "fill": True,
            "lineTension": 0.1,
            "backgroundColor": secondary,
            "borderColor": primary,
            "borderCapStyle": "butt",
            "border_dash": [],
            "border_dash_offset": 0.0,
            "borderJoinStyle": "miter",
            "pointBorderColor": primary,
            "pointBackgroundColor": primary,
            "pointBorderWidth": 2,
            "pointhoverRadius": 8,
            "pointHoverBackgroundColor": primary,
            "pointHoverBorderColor": primary,
            "pointHoverBorderWidth": 4,
            "pointRadius": 2,
            "pointHitRadius": 8,
            "maintainAspectRatio": False,
            "data": values,
        }
        return dataset

    def _get_correct_day(self, day_number):
        # Return Sunday=1 through Saturday=7.
        days = {"1": 6, "2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5}
        return days.get(day_number)

    def _get_month_payments(self, user, current_year, query, category=None):
        """ Return month payments for a year from a request
        :arg user object
        :type user: User
        :arg category: A category to filter through
        :type category: string
        :returns: A list with the amounts in income for every month
        :rtype: list

        """
        data = (
            query.annotate(month=ExtractMonth("created__day"))
            .values("month")
            .annotate(
                amount=Sum("payment__amount"),
                category=F("payment__order__product__categories__name"),
            )
        )
        group_by_value: dict = defaultdict(list)
        for value in data:
            if (
                group_by_value is not None
                and len(group_by_value[value.get("category")]) == 0
            ):
                group_by_value[value.get("category")] = [
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ]
            group_by_value[value.get("category")][value.get("month") - 1] = value.get(
                "amount"
            )
        return group_by_value

    def _get_week_payments(
        self, user, current_year, query, start_week, end_week, category=None
    ):
        """ Return week payments for a year
        :arg user object
        :type user: User
        :arg category: A category to filter through
        :type category: string
        :returns: A list with the amounts in income for every month
        :rtype: list

        """
        data = (
            query.filter(created__range=[start_week, end_week])
            .annotate(day=ExtractWeekDay("created__day"))
            .values("day")
            .annotate(
                amount=Sum("payment__amount"),
                category=F("payment__order__product__categories__name"),
            )
        )
        group_by_value: dict = defaultdict(list)
        for value in data:
            if (
                group_by_value is not None
                and len(group_by_value[value.get("category")]) == 0
            ):
                group_by_value[value.get("category")] = [0, 0, 0, 0, 0, 0, 0]
            day_number = self._get_correct_day(str(value.get("day")))
            group_by_value[value.get("category")][day_number] = value.get("amount")
        return group_by_value

    def _datasets(
        self,
        request,
        categories,
        query,
        data_type="month",
        start_week=None,
        end_week=None,
    ):
        week_datasets = []
        month_datasets = []
        current_year = (
            datetime.date.today().year
        )  # TODO In future needs to make it variable
        month_labels = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        week_labels = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saterday",
            "Sunday",
        ]
        month_payments_data = self._get_month_payments(
            request.user, current_year, query, category=None
        )
        week_payments_data = self._get_week_payments(
            request.user,
            current_year,
            query,
            category=None,
            start_week=start_week,
            end_week=end_week,
        )
        category_count_week = 0
        category_count_month = 0
        for category, values in week_payments_data.items():
            category_count_week = category_count_week + 1
            line_data = self._line_chart(
                values=values, label=category, category_count=category_count_week
            )
            week_datasets.append(line_data)

        for category, values in month_payments_data.items():
            category_count_month = category_count_month + 1
            line_data = self._line_chart(
                values=values, label=category, category_count=category_count_month
            )
            month_datasets.append(line_data)

        income_data = {
            "income_data": {
                "week": {
                    "labels": week_labels if week_labels else [],
                    "datasets": week_datasets if week_datasets else [],
                },
                "month": {
                    "labels": month_labels if month_labels else [],
                    "datasets": month_datasets if month_datasets else [],
                },
            }
        }
        return income_data

    def get(self, request, pk=None, format=None, data_type="month"):

        date = datetime.date.today()
        start_week = date - datetime.timedelta(date.weekday())
        end_week = start_week + datetime.timedelta(7)
        user = request.user
        categories = (
            user.vendor.products.annotate(category=F("categories__name"))
            .values_list("category", flat=True)
            .order_by("categories__name")
        )

        query = (
            user.vendor.transactions.only(
                "id", "payment__amount", "payment", "created"
            )
            .filter(
                created__year=datetime.date.today().year,
                payment__isnull=False,
                payment__amount__gte=0,
                payment__order__status="completed"
            )
            .order_by("payment__order__product__categories__name")
        )

        totals = query.aggregate(
            # day_total_earned=Sum("payment__amount", filters=Q(created=datetime.date.today())),
            week_total_earned=Sum(
                "payment__amount", filter=Q(created__range=[start_week, end_week])
            ),
            # month_total_earned=Sum("payment__amount", filters=Q(created=datetime.date.today().month)),
            total_earned=Sum("payment__amount"),
        )

        amount = DecimalFunc(F("payment__amount"))

        # # prevent divison by zero
        if totals.get("total_earned") != 0:
            month_expresion = ExpressionWrapper(
                amount / totals.get("total_earned") * 100, output_field=DecimalField()
            )
        else:
            month_expresion = ExpressionWrapper(amount, output_field=DecimalField())

        if totals.get("total_earned") != 0:
            week_expresion = ExpressionWrapper(
                amount / Value(totals.get("week_total_earned")) * 100,
                output_field=DecimalField(),
            )
        else:
            week_expresion = ExpressionWrapper(amount, output_field=DecimalField())

        month_progress_query = (
            query.annotate(month=ExtractMonth("created__day"))
            .values("month")
            .annotate(
                amount=Sum("payment__amount"),
                percentage=RoundFunc(Sum(month_expresion), 2),
                label=F("payment__order__product__categories__name"),
            )
        )
        week_progress_query = (
            query.filter(created__date__range=[start_week, end_week])
            .annotate(week=ExtractWeek("created__week"))
            .values("week")
            .annotate(
                amount=Sum("payment__amount"),
                percentage=RoundFunc(Sum(week_expresion), 2),
                label=F("payment__order__product__categories__name"),
            )
        )

        progress_count = 0
        progress_week = None
        progress_month = None
        progress_week_list = []
        progress_month_list = []
        for progress_week, progress_month in itertools.zip_longest(
            week_progress_query, month_progress_query
        ):
            progress_count = progress_count + 1
            if progress_week:
                progress_week.update({"color": color_list[progress_count]})
                progress_week_list.append(progress_week)
            if progress_month:
                progress_month.update({"color": color_list[progress_count]})
                progress_month_list.append(progress_month)
        progress_data = {
            "progress_bar_data": {
                "week": progress_week_list,
                "month": progress_month_list,
            }
        }

        data = self._datasets(
            request,
            categories,
            query=query,
            data_type=data_type,
            start_week=start_week,
            end_week=end_week,
        )
        data.update(progress_data)
        return Response(data, status=200)


class MainDashboardApiView(APIView):
    def get(self, request, pk=None, format=None):
        user = request.user
        orders = (
            Order.objects.filter(payment__transaction__vendor__user=user)
            .annotate(product_name=F("product__title"))
            .order_by("id")
            .values(
                "id", "product_name", "status", "created", amount=F("payment__amount")
            )
        )
        reviews = ProductReview.objects.filter(
            product__vendor__user=user
        ).order_by("id")[:5]
        disputes = Dispute.objects.filter(vendor__user=user,)[:5]
        total_products = Product.objects.filter(vendor__user=user).count()
        payments = user.vendor.transactions.values(
            "payment", "created", "payment__order__status"
        ).filter(payment__isnull=False, payout__isnull=True)

        earned_today = payments.filter(
            created__startswith=datetime.date.today(),
            payment__order__status="completed"
        ).aggregate(earned_today=Coalesce(Sum("payment__amount"), 0))
        total_earned = payments.filter(
            payment__order__status="completed"
        ).aggregate(
            total_earned=Coalesce(Sum("payment__amount"), 0)
        )
        disputes = Dispute.objects.filter(vendor=user.vendor)
        total_payout = (
            user.vendor.transactions.values("payout")
            .filter(payment__isnull=True, payout__isnull=False)
        )
        serializer = MainDashboardSerializer(
            {
                "orders": orders[:5],
                "reviews": reviews,
                "disputes": disputes,
                "earned_today": earned_today.get("earned_today"),
                "total_products": total_products,
                "total_orders": orders.count(),
                "total_earned": total_earned.get("total_earned"),
                "total_payments": payments.count(),
                "total_disputes": disputes.count(),
                "total_reviews": reviews.count(),
                "total_payout": total_payout.count(),
            },
            context={"request": self.request},
        )
        if serializer:
            return Response(serializer.data)
        return Response(data={"error": "Something went wrong."})


class DashboardBalanceApiView(APIView):
    def get(self, request, pk=None, format=None):
        user = request.user
        pending = Payment.objects.filter(
            transaction__vendor=user.vendor,
            status="pending",
            order__status=Order.PENDING,
        )
        if user and user.vendor.balance:
            available_payout = user.vendor.balance.available_payout
            last_payout = Payout.objects.filter(
                transaction__vendor=user.vendor, status="omw"
            ).last()
            invoices = Payment.objects.filter(transaction__vendor=user.vendor).values(
                "status", "amount", product_name=F("order__product__title")
            )
            transactions = (
                Transaction.objects.filter(vendor=user.vendor)
                .annotate(
                    day=ExtractDay("created"),
                    month=ExtractMonth("created"),
                    type=F("_type"),
                    amount=Case(
                        When(payment__amount__gte=0, then=F("payment__amount")),
                        When(payout__amount__gte=0, then=F("payout__amount")),
                        default=Value(0),
                        output_field=DecimalField(),
                    ),
                    _from=Case(
                        When(payment__isnull=False, then=Value("From customer")),
                        When(payout__isnull=False, then=Value("From application")),
                        default=None,
                        output_field=CharField(),
                    ),
                    currency=Case(
                        When(payment=True, then=Value("USD")),
                        When(payout=True, then=Value("USD")),
                        default=Value("USD"),
                        output_field=CharField(),
                    ),
                )
                .values("day", "month", "type", "amount", "_from", "currency")
            )
            transaction_data = TransactionOperationSerializer(transactions[:10], many=True)
            invoice_data = TransactionInvoiceSerializer(invoices[:10], many=True)
            return Response(
                data={
                    "balance": user.vendor.balance.available,
                    "available_payout": available_payout,
                    "pending": pending.aggregate(amount=Sum("amount")).get("amount"),
                    "last_payout": last_payout.amount if last_payout else None,
                    "operations": transaction_data.data,
                    "invoices": invoice_data.data,
                }
            )
        else:
            return Response(data=None)


class BankWithdrawApiView(APIView):
    def post(self, request, pk=None, format=None):
        user = request.user
        vendor_balance_withdraw = VendorBalanceWithdraw(user)
        serializer = WithdrawSerializer(data=request.data)
        if serializer.is_valid():
            response = vendor_balance_withdraw.create_payout(
                amount=serializer.data.get("amount")
            )
            return Response(data=response)
        else:
            return Response(data={"message": "Something went wrong"}, status=400)
