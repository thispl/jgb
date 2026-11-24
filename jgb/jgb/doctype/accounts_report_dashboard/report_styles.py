# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# Shared styling helpers for Accounts Report Dashboard Excel exports.
# Provides consistent currency formatting, colors, fonts and borders across all reports.

from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
COLOR_HEADER_BG = '1F3864'        # dark navy blue
COLOR_HEADER_FG = 'FFFFFF'        # white
COLOR_TITLE = '1F3864'            # dark navy blue
COLOR_COMPANY = '1F3864'
COLOR_DATE = '404040'             # dark grey
COLOR_SUBTOTAL_BG = 'D9E1F2'      # light blue
COLOR_SUBTOTAL_FG = '1F3864'
COLOR_CUST_SUBTOTAL_BG = 'E9EEF7' # very light blue (customer subtotal)
COLOR_CUST_SUBTOTAL_FG = '1F3864'
COLOR_GRAND_TOTAL_BG = '1F3864'   # dark navy blue
COLOR_GRAND_TOTAL_FG = 'FFFFFF'
COLOR_SALESPERSON_BG = '4472C4'   # medium blue
COLOR_SALESPERSON_FG = 'FFFFFF'
COLOR_ALT_ROW = 'F2F2F2'          # light grey for alternating rows
COLOR_BORDER = 'B4B4B4'           # light grey border

# ---------------------------------------------------------------------------
# Fills
# ---------------------------------------------------------------------------
header_fill = PatternFill(start_color=COLOR_HEADER_BG, end_color=COLOR_HEADER_BG, fill_type='solid')
subtotal_fill = PatternFill(start_color=COLOR_SUBTOTAL_BG, end_color=COLOR_SUBTOTAL_BG, fill_type='solid')
cust_subtotal_fill = PatternFill(start_color=COLOR_CUST_SUBTOTAL_BG, end_color=COLOR_CUST_SUBTOTAL_BG, fill_type='solid')
grand_total_fill = PatternFill(start_color=COLOR_GRAND_TOTAL_BG, end_color=COLOR_GRAND_TOTAL_BG, fill_type='solid')
salesperson_fill = PatternFill(start_color=COLOR_SALESPERSON_BG, end_color=COLOR_SALESPERSON_BG, fill_type='solid')
alt_row_fill = PatternFill(start_color=COLOR_ALT_ROW, end_color=COLOR_ALT_ROW, fill_type='solid')

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
header_font = Font(bold=True, color=COLOR_HEADER_FG, size=11, name='Calibri')
title_font = Font(bold=True, size=16, color=COLOR_TITLE, name='Calibri')
company_font = Font(bold=True, size=12, color=COLOR_COMPANY, name='Calibri')
date_font = Font(bold=True, size=10, color=COLOR_DATE, name='Calibri')
subtotal_font = Font(bold=True, size=11, color=COLOR_SUBTOTAL_FG, name='Calibri')
cust_subtotal_font = Font(bold=True, size=10, color=COLOR_CUST_SUBTOTAL_FG, name='Calibri')
grand_total_font = Font(bold=True, size=12, color=COLOR_GRAND_TOTAL_FG, name='Calibri')
salesperson_font = Font(bold=True, size=13, color=COLOR_SALESPERSON_FG, name='Calibri')
data_font = Font(size=10, name='Calibri')
bold_font = Font(bold=True, size=11, name='Calibri')

# ---------------------------------------------------------------------------
# Alignments
# ---------------------------------------------------------------------------
align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
align_right = Alignment(horizontal='right', vertical='center', wrap_text=True)
align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

# ---------------------------------------------------------------------------
# Borders
# ---------------------------------------------------------------------------
thin_side = Side(style='thin', color=COLOR_BORDER)
border_thin = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

# ---------------------------------------------------------------------------
# Number format for currency columns (negative in red)
# ---------------------------------------------------------------------------
currency_format = '#,##0.00;[Red](#,##0.00);-'


def apply_title_rows(ws, num_cols, title_text, company=None, report_date=None):
    """Style the first 3 rows: company (row 1), title (row 2), date (row 3).

    Row 4 is left blank as a spacer.  Header row is expected at row 5.
    """
    # Row 1 - company
    for cell in ws[1]:
        cell.font = company_font
        cell.alignment = align_center
    # Row 2 - title
    for cell in ws[2]:
        cell.font = title_font
        cell.alignment = align_center
    # Row 3 - date
    for cell in ws[3]:
        cell.font = date_font
        cell.alignment = align_center

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=num_cols)

    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 28
    ws.row_dimensions[3].height = 20


def apply_header_row(ws, header_row_idx, num_cols):
    """Apply the dark-navy header styling to a row."""
    for cell in ws[header_row_idx]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = border_thin
    ws.row_dimensions[header_row_idx].height = 25


def style_data_row(row, num_cols, text_cols, is_subtotal=False, is_grand_total=False,
                   is_salesperson=False, alt_row=False, merge_cols=None,
                   is_customer_subtotal=False):
    """Style a single data row in-place.

    text_cols: number of leading columns that should be left-aligned (text).
    is_subtotal / is_grand_total / is_salesperson: special row types.
    is_customer_subtotal: customer-level subtotal (lighter shade).
    alt_row: apply alternating row fill.
    merge_cols: number of columns to merge for subtotal/grand-total/salesperson rows.
    """
    for i, cell in enumerate(row):
        cell.border = border_thin

        if is_salesperson:
            cell.font = salesperson_font
            cell.fill = salesperson_fill
            cell.alignment = align_center

        elif is_grand_total:
            cell.font = grand_total_font
            cell.fill = grand_total_fill
            cell.alignment = align_left if i < text_cols else align_right
            if i >= text_cols:
                cell.number_format = currency_format

        elif is_customer_subtotal:
            cell.font = cust_subtotal_font
            cell.fill = cust_subtotal_fill
            cell.alignment = align_left if i < text_cols else align_right
            if i >= text_cols:
                cell.number_format = currency_format

        elif is_subtotal:
            cell.font = subtotal_font
            cell.fill = subtotal_fill
            cell.alignment = align_left if i < text_cols else align_right
            if i >= text_cols:
                cell.number_format = currency_format

        else:
            cell.font = data_font
            cell.alignment = align_left if i < text_cols else align_right
            if i >= text_cols:
                cell.number_format = currency_format
            if alt_row:
                cell.fill = alt_row_fill


def apply_currency_format(ws, start_row, end_row, start_col, end_col):
    """Apply the currency number format to a rectangular range of cells."""
    for row in ws.iter_rows(min_row=start_row, max_row=end_row, min_col=start_col, max_col=end_col):
        for cell in row:
            cell.number_format = currency_format


def setup_page(ws, orientation='landscape'):
    """Common page setup for printing."""
    ws.page_setup.orientation = orientation
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
