# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, money_in_words


class ProformaInvoice(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        # Always recalculate line amounts so qty/rate edits are reflected.
        items_total = 0
        for item in self.items:
            item.amount = flt(item.qty) * flt(item.rate)
            items_total += flt(item.amount)

        if self.sales_order:
            # For proformas linked to a Sales Order, total_so /
            # total_taxes_and_charges_so are seeded from the SO (base_net_total /
            # total_taxes_and_charges) and already include any SO-level additional
            # discount. Line-item amounts don't include that discount, so instead of
            # re-summing directly we scale the items total by factors seeded on first
            # save: so_total_factor preserves the SO-level discount ratio and
            # so_tax_factor preserves the effective tax rate. When the user edits
            # item quantities, totals adjust proportionally.
            # Seed the ratios from the Sales Order itself, NOT from this doc's
            # current total_so / total_taxes_and_charges_so: the client already
            # sets total_so to the (scaled) items total, so seeding the factor
            # from it applies the ratio a second time and shrinks the total
            # (e.g. JGB-ADV-2026-00197, whose items were reduced to a subset and
            # whose total_so came out ~57% too low).
            so = (
                frappe.get_doc("Sales Order", self.sales_order)
                if frappe.db.exists("Sales Order", self.sales_order)
                else None
            )
            so_items_total = sum(flt(i.amount) for i in so.items) if so else 0

            if not self.so_total_factor:
                self.so_total_factor = (
                    flt(so.base_net_total) / so_items_total if so_items_total else 1
                )
            if not self.so_tax_factor:
                self.so_tax_factor = (
                    flt(so.total_taxes_and_charges) / flt(so.base_net_total)
                    if so and flt(so.base_net_total)
                    else 0
                )

            self.total_so = items_total * flt(self.so_total_factor)
            self.total_taxes_and_charges_so = flt(self.total_so) * flt(self.so_tax_factor)
        else:
            # Keep the original totals before we change them so the tax rate
            # is calculated from the original tax / original total.
            original_total = flt(self.total_so)
            original_tax = flt(self.total_taxes_and_charges_so)

            self.total_so = items_total

            # Recalculate taxes proportionally when rows change
            if original_total and original_tax:
                tax_rate = original_tax / original_total
                self.total_taxes_and_charges_so = flt(self.total_so) * tax_rate
            else:
                self.total_taxes_and_charges_so = 0

        self.grand_total_so = flt(self.total_so) + flt(self.total_taxes_and_charges_so)

        # Recalculate advance amounts from the percentage
        percent = flt(self.percent) or 0
        self.total_adv = self.total_so * percent / 100
        self.total_taxes_and_charges_adv = self.total_taxes_and_charges_so * percent / 100
        self.grand_total_adv = self.total_adv + self.total_taxes_and_charges_adv

        if self.grand_total_adv:
            self.advance_words = money_in_words(self.grand_total_adv)
        else:
            self.advance_words = ""
