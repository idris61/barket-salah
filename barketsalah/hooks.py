app_name = "barketsalah"
app_title = "Barketsalah"
app_publisher = "barketsalah"
app_description = "barketsalah"
app_email = "developerinfo64@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "barketsalah",
# 		"logo": "/assets/barketsalah/logo.png",
# 		"title": "Barketsalah",
# 		"route": "/barketsalah",
# 		"has_permission": "barketsalah.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/barketsalah/css/barketsalah.css"
# app_include_js = "/assets/barketsalah/js/barketsalah.js"

# include js, css files in header of web template
# web_include_css = "/assets/barketsalah/css/barketsalah.css"
# web_include_js = "/assets/barketsalah/js/barketsalah.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "barketsalah/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Opportunity": "public/js/opportunity.js",
	"Sales Order": "public/js/sales_order.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "barketsalah/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "barketsalah.utils.jinja_methods",
# 	"filters": "barketsalah.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "barketsalah.install.before_install"
# after_install = "barketsalah.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "barketsalah.uninstall.before_uninstall"
# after_uninstall = "barketsalah.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "barketsalah.utils.before_app_install"
# after_app_install = "barketsalah.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "barketsalah.utils.before_app_uninstall"
# after_app_uninstall = "barketsalah.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "barketsalah.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }


fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["module", "=", "Barketsalah"]],
	}
]

doc_events = {
	"Quotation": {
		"before_validate": "barketsalah.api.quote_to_salesorder.prepare_quote_items_for_sales_order",
		"before_save": "barketsalah.api.setup.quotation_before_save",
	}
}

# Document Events
# ---------------

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"barketsalah.tasks.all"
# 	],
# 	"daily": [
# 		"barketsalah.tasks.daily"
# 	],
# 	"hourly": [
# 		"barketsalah.tasks.hourly"
# 	],
# 	"weekly": [
# 		"barketsalah.tasks.weekly"
# 	],
# 	"monthly": [
# 		"barketsalah.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "barketsalah.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "barketsalah.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "barketsalah.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "barketsalah.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["barketsalah.utils.before_request"]
# after_request = ["barketsalah.utils.after_request"]

# Job Events
# ----------
# before_job = ["barketsalah.utils.before_job"]
# after_job = ["barketsalah.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"barketsalah.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
