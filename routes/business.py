"""
Raw to Ready business expenses, with GST capture for input credit.

Kept separate from personal expenses on purpose - different fields, different
reader (your CA), and it stays out of the Family page that other household
members can see.
"""

import csv
import io
import re
from datetime import date, datetime

from flask import (Blueprint, render_template, request, jsonify, Response,
                   current_app)
from flask_login import login_required, current_user
from sqlalchemy import func, extract

from models import db, BusinessExpense

business = Blueprint('business', __name__)


@business.before_request
@login_required
def admin_only():
    """Hiding the nav link is not security. Every route in this blueprint is
    blocked for non-admins, so a family member cannot reach the business books
    by typing the URL."""
    if current_user.role != 'admin':
        return jsonify({'success': False,
                        'message': 'Not available for this profile.'}), 403

CATEGORIES = [
    'Software & Subscriptions',
    'Hosting & Domain',
    'Professional Fees',
    'Marketing & Advertising',
    'Freelancer Payments',
    'Travel & Conveyance',
    'Office & Utilities',
    'Equipment & Hardware',
    'Bank & Payment Charges',
    'Training & Books',
    'Other',
]

GST_RATES = [0, 5, 12, 18, 28]
PAYMENT_MODES = ['UPI', 'Bank Transfer', 'Credit Card', 'Debit Card', 'Cash', 'Auto-debit']

# 2 digits state code, 10 char PAN, 1 entity digit, 1 'Z', 1 checksum
GSTIN_RE = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')


def _quarter_bounds(d):
    """Return (start, end, label) of the Indian FY quarter containing d."""
    y, m = d.year, d.month
    if m in (4, 5, 6):
        return date(y, 4, 1), date(y, 6, 30), f'Q1 Apr-Jun {y}'
    if m in (7, 8, 9):
        return date(y, 7, 1), date(y, 9, 30), f'Q2 Jul-Sep {y}'
    if m in (10, 11, 12):
        return date(y, 10, 1), date(y, 12, 31), f'Q3 Oct-Dec {y}'
    return date(y, 1, 1), date(y, 3, 31), f'Q4 Jan-Mar {y}'


def _split_gst(taxable, rate, supply_type):
    """Work out CGST/SGST/IGST from the taxable value and rate."""
    taxable = float(taxable or 0)
    rate = float(rate or 0)
    gst = round(taxable * rate / 100.0, 2)
    if supply_type == 'inter':
        return 0.0, 0.0, gst
    if supply_type == 'intra':
        half = round(gst / 2.0, 2)
        # keep the halves summing to the whole after rounding
        return half, round(gst - half, 2), 0.0
    return 0.0, 0.0, 0.0


@business.route('/business')
@login_required
def index():
    today = date.today()
    q_start, q_end, q_label = _quarter_bounds(today)

    rows = BusinessExpense.query.filter_by(user_id=current_user.id)\
        .order_by(BusinessExpense.date.desc(), BusinessExpense.id.desc()).all()

    # This quarter - the numbers that matter at QRMP filing time
    q_rows = [r for r in rows if q_start <= r.date <= q_end]
    q_taxable = sum(r.taxable_value or 0 for r in q_rows)
    q_gst = sum(r.gst_amount for r in q_rows)
    q_total = sum(r.total_amount or 0 for r in q_rows)
    q_claimable = sum(r.gst_amount for r in q_rows if r.claim_input_credit)

    # This month
    m_rows = [r for r in rows if r.date.year == today.year and r.date.month == today.month]
    m_total = sum(r.total_amount or 0 for r in m_rows)

    # This financial year (April to March)
    fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    fy_rows = [r for r in rows if r.date >= fy_start]
    fy_total = sum(r.total_amount or 0 for r in fy_rows)
    fy_label = f"FY {fy_start.year}-{str(fy_start.year + 1)[-2:]}"

    # Category breakdown for the financial year
    cat_totals = {}
    for r in fy_rows:
        cat_totals[r.category] = cat_totals.get(r.category, 0) + (r.total_amount or 0)
    cat_totals = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)

    # Entries missing a GSTIN but carrying GST - these are the ones that will
    # cost you input credit if not fixed before filing.
    missing_gstin = [r for r in q_rows if r.gst_amount > 0 and not r.vendor_gstin]

    return render_template(
        'business.html',
        expenses=rows,
        categories=CATEGORIES,
        gst_rates=GST_RATES,
        payment_modes=PAYMENT_MODES,
        quarter_label=q_label,
        q_taxable=q_taxable, q_gst=q_gst, q_total=q_total, q_claimable=q_claimable,
        q_count=len(q_rows),
        month_total=m_total, month_count=len(m_rows),
        fy_total=fy_total, fy_label=fy_label,
        cat_totals=cat_totals,
        missing_gstin=missing_gstin,
        today=today.isoformat(),
    )


@business.route('/business/add', methods=['POST'])
@login_required
def add():
    data = request.get_json(silent=True) or {}
    try:
        vendor = (data.get('vendor_name') or '').strip()
        category = (data.get('category') or '').strip()
        if not vendor:
            return jsonify({'success': False, 'message': 'Vendor name is required.'}), 400
        if not category:
            return jsonify({'success': False, 'message': 'Please choose a category.'}), 400

        taxable = float(data.get('taxable_value') or 0)
        if taxable <= 0:
            return jsonify({'success': False,
                            'message': 'Taxable value must be more than 0.'}), 400

        rate = float(data.get('gst_rate') or 0)
        supply_type = data.get('supply_type') or 'intra'
        if rate == 0:
            supply_type = 'none'

        gstin = (data.get('vendor_gstin') or '').strip().upper()
        if gstin and not GSTIN_RE.match(gstin):
            return jsonify({'success': False,
                            'message': 'That GSTIN does not look valid. It should be '
                                       '15 characters, e.g. 24ABCDE1234F1Z5.'}), 400

        cgst, sgst, igst = _split_gst(taxable, rate, supply_type)
        total = round(taxable + cgst + sgst + igst, 2)

        exp = BusinessExpense(
            user_id=current_user.id,
            date=datetime.strptime(data['date'], '%Y-%m-%d').date()
            if data.get('date') else date.today(),
            vendor_name=vendor,
            vendor_gstin=gstin or None,
            invoice_number=(data.get('invoice_number') or '').strip() or None,
            category=category,
            taxable_value=taxable,
            gst_rate=rate,
            supply_type=supply_type,
            cgst=cgst, sgst=sgst, igst=igst,
            total_amount=total,
            payment_mode=(data.get('payment_mode') or '').strip() or None,
            claim_input_credit=bool(data.get('claim_input_credit', True)) and rate > 0,
            notes=(data.get('notes') or '').strip() or None,
        )
        db.session.add(exp)
        db.session.commit()
        return jsonify({'success': True, 'total': total,
                        'gst': round(cgst + sgst + igst, 2)})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False,
                        'message': f'Please check the numbers and date. ({e})'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('business expense add failed')
        return jsonify({'success': False, 'message': str(e)}), 400


@business.route('/business/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete(expense_id):
    exp = BusinessExpense.query.filter_by(
        id=expense_id, user_id=current_user.id
    ).first()
    if not exp:
        return jsonify({'success': False, 'message': 'Entry not found.'}), 404
    db.session.delete(exp)
    db.session.commit()
    return jsonify({'success': True})


@business.route('/business/export/csv')
@login_required
def export_csv():
    """Quarterly or full-year export for GSTR-3B input credit and the CA.

    ?period=quarter  - the current QRMP quarter (default)
    ?period=fy       - the whole financial year
    ?period=all      - everything
    """
    period = request.args.get('period', 'quarter')
    today = date.today()

    q = BusinessExpense.query.filter_by(user_id=current_user.id)
    if period == 'quarter':
        start, end, label = _quarter_bounds(today)
        q = q.filter(BusinessExpense.date >= start, BusinessExpense.date <= end)
    elif period == 'fy':
        start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
        end = date(start.year + 1, 3, 31)
        label = f'FY {start.year}-{str(start.year + 1)[-2:]}'
        q = q.filter(BusinessExpense.date >= start, BusinessExpense.date <= end)
    else:
        label = 'All'

    rows = q.order_by(BusinessExpense.date).all()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([f'Raw to Ready - Business Expenses ({label})'])
    w.writerow([f'Generated {today.strftime("%d %b %Y")}'])
    w.writerow([])
    w.writerow(['Date', 'Vendor', 'Vendor GSTIN', 'Invoice No', 'Category',
                'Taxable Value', 'GST Rate %', 'Supply', 'CGST', 'SGST', 'IGST',
                'Total', 'Input Credit Claimable', 'Payment Mode', 'Notes'])

    t_taxable = t_cgst = t_sgst = t_igst = t_total = t_claim = 0
    for r in rows:
        w.writerow([
            r.date.strftime('%d-%m-%Y'), r.vendor_name, r.vendor_gstin or '',
            r.invoice_number or '', r.category,
            f'{r.taxable_value:.2f}', f'{r.gst_rate:.0f}',
            {'intra': 'Intra-state', 'inter': 'Inter-state'}.get(r.supply_type, '-'),
            f'{r.cgst:.2f}', f'{r.sgst:.2f}', f'{r.igst:.2f}',
            f'{r.total_amount:.2f}',
            'Yes' if r.claim_input_credit else 'No',
            r.payment_mode or '', (r.notes or '').replace('\n', ' '),
        ])
        t_taxable += r.taxable_value or 0
        t_cgst += r.cgst or 0
        t_sgst += r.sgst or 0
        t_igst += r.igst or 0
        t_total += r.total_amount or 0
        if r.claim_input_credit:
            t_claim += r.gst_amount

    w.writerow([])
    w.writerow(['TOTALS', '', '', '', '', f'{t_taxable:.2f}', '', '',
                f'{t_cgst:.2f}', f'{t_sgst:.2f}', f'{t_igst:.2f}',
                f'{t_total:.2f}', '', '', ''])
    w.writerow([])
    w.writerow(['Input credit claimable this period', f'{t_claim:.2f}'])
    w.writerow(['Note', 'Figures are as entered. Verify against invoices '
                        'before filing GSTR-3B.'])

    filename = f'raw-to-ready-expenses-{label.replace(" ", "-").lower()}.csv'
    return Response(
        out.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )
