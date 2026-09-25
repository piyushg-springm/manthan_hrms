import click

from manthan_hrms.compliance.company import sync_all_companies
from manthan_hrms.setup.custom_fields import make_custom_fields


def after_install():
	make_custom_fields()
	# Site-specific setup (company, departments, leave policy, sample data) is run explicitly per
	# client site, e.g. `bench --site <site> execute manthan_hrms.setup.day1.run_sprint1`.
	click.secho("Manthan HRMS installed. Run manthan_hrms.setup.day1 to set up the client company.", fg="green")


def after_migrate():
	make_custom_fields()
	sync_all_companies()
