# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ShippingRequest(Document):
	def validate(self):
		if self.dangerous_goods and not self.dangerous_doc:
			frappe.throw(_("Please upload a document in the Dangerous Doc field when Dangerous Goods is checked."))
