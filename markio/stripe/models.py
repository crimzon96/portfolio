@property
def to_dict(self):
    """ Turn Product to dict variables"""
    obj_dict = {}
    strategy = Selector().strategy()
    info = strategy.fetch_for_product(self)
    for attribute in self.__dict__:
        if not hasattr(attribute, "attr") and attribute not in [
            "_state",
            "structure",
            "is_public",
            "product_class_id",
            "rating",
            "parent_id",
            "date_updated",
            "date_created",
            "is_discountable",
            "attr",
        ]:
            obj_dict.update({attribute: getattr(self, attribute)})
        if attribute == "attr":
            attrs = (
                self.attributes.all()
                .annotate(value=F("productattributevalue__value_option__option"))
                .values("code", "name", "value")
            )
            attr_list = []
            for attr in attrs:
                attr_list.append(
                    {
                        "name": attr.get("name"),
                        "code": attr.get("code"),
                        "value": attr.get("value"),
                    }
                )
            obj_dict.update({"attributes": attr_list})
    # obj_dict.update({"price": info.price})
    return obj_dict

@property
def stockrecord(self):
    return self.stockrecords.first()

@property
def to_line_item(self):
    line_object = {
        "name": self.title,
        "currency": "eur",
    }
    return line_object

@cached_property
def cached_reviews(self):
    return self.reviews
