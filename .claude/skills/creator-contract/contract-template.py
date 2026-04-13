"""
MFL Affiliate Contract PDF Generator — Template

Usage:
    python3 contract-template.py \
        --name "Full Legal Name" \
        --entity "Sole Trader" \
        --address "123 Street, City, Postcode, Country" \
        --alias "Operating Name" \
        --start-date "March 1st, 2026" \
        --guarantee "200 EUR/month" \
        --deliverables "1 dedicated MFL video content (weekly)|1 MFL integration in a Football Manager video (weekly)|4 Twitter/X posts about MFL content (weekly)" \
        --output "/Users/mathurin/Downloads/Affiliate Contract - Name _ MFL (DRAFT).pdf"

All arguments are optional. Missing values will use XXXXX placeholders.
Deliverables are pipe-separated.
"""

import argparse
from fpdf import FPDF


class ContractPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def reset_x(self):
        self.set_x(self.l_margin)

    def chapter_title(self, title):
        self.reset_x()
        self.set_font("Helvetica", "B", 14)
        self.ln(5)
        self.multi_cell(w=0, h=10, text=title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def section_title(self, title):
        self.reset_x()
        self.set_font("Helvetica", "B", 11)
        self.ln(3)
        self.multi_cell(w=0, h=8, text=title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text, space_after=True):
        self.reset_x()
        self.set_font("Helvetica", "", 10)
        self.multi_cell(w=0, h=6, text=text, new_x="LMARGIN", new_y="NEXT")
        if space_after:
            self.ln(2)

    def inline_bold(self, bold_text, normal_text=""):
        self.set_font("Helvetica", "B", 10)
        self.write(6, bold_text)
        if normal_text:
            self.set_font("Helvetica", "", 10)
            self.write(6, normal_text)

    def inline_normal(self, text):
        self.set_font("Helvetica", "", 10)
        self.write(6, text)

    def sig_block(self, affiliate_name):
        self.ln(10)
        y = self.get_y()
        if y > 230:
            self.add_page()
        x_left = self.l_margin
        x_right = 110
        self.set_font("Helvetica", "", 10)

        y = self.get_y()
        self.set_xy(x_left, y)
        self.cell(70, 7, "For and on behalf of Affiliate")
        self.set_xy(x_right, y)
        self.cell(70, 7, "For and on behalf of Customer")

        y += 12
        self.set_xy(x_left, y)
        self.cell(70, 7, f"Name: {affiliate_name}")
        self.set_xy(x_right, y)
        self.cell(70, 7, "Name: Mathurin Blouin, CEO")

        y += 12
        self.set_xy(x_left, y)
        self.cell(70, 7, "Date:")
        self.set_xy(x_right, y)
        self.cell(70, 7, "Date:")

        y += 12
        self.set_xy(x_left, y)
        self.cell(70, 7, "Signature:")
        self.set_xy(x_right, y)
        self.cell(70, 7, "Signature:")
        self.ln(10)


def generate_contract(
    name="XXXXX",
    entity="XXXXX",
    address="XXXXX",
    alias="XXXXX",
    start_date="XXXXX",
    guarantee="XXXXX",
    deliverables=None,
    output_path=None,
    no_conflict_clause=False,
    initial_term=None,
    pack_bonus=None,
    welcome_bonus=None,
    welcome_bonus_reason=None,
    revenue_cap="one year",
    commission_tiers=None,
    representative=None,
    payment_threshold=None,
):
    no_guarantee = guarantee and guarantee.lower() == "none"
    no_deliverables = deliverables is not None and len(deliverables) == 1 and deliverables[0].lower() == "none"
    if deliverables is None:
        deliverables = ["XXXXX"]

    if output_path is None:
        safe_alias = alias if alias != "XXXXX" else "Creator"
        slug = safe_alias.lower().replace(" ", "-")
        output_path = f"creators-management/creators/{slug}/Affiliate Contract - {safe_alias} _ MFL (DRAFT).pdf"

    pdf = ContractPDF()
    pdf.set_margins(25, 25, 25)

    # ===================== PAGE 1: COVER =====================
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font("Helvetica", "B", 32)
    pdf.multi_cell(w=0, h=15, text="Affiliate Contract", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(40)

    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(w=0, h=8, text="Prepared for:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    if representative:
        pdf.multi_cell(w=0, h=8, text=representative, new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(w=0, h=8, text=name, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(w=0, h=8, text=name, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)

    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(w=0, h=8, text="Created by:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(w=0, h=8, text="Mathurin Blouin, CEO", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(w=0, h=8, text="Meta Football League (MFL)", new_x="LMARGIN", new_y="NEXT")

    # ===================== PAGE 2: MAIN CONTRACT =====================
    pdf.add_page()

    # Opening paragraph with inline bold
    pdf.reset_x()
    pdf.inline_bold("This Affiliate Contract ")
    pdf.inline_normal(
        '(this "Contract" or this "Affiliate Contract"), is entered into and made effective as of '
    )
    pdf.inline_bold(start_date)
    pdf.inline_normal(' (the "Effective Date"), by and between:')
    pdf.ln(10)

    # Party 1
    pdf.reset_x()
    pdf.inline_normal("(1) ")
    pdf.inline_bold("Meta Football League")
    pdf.inline_normal(
        ", a company registered in France under SIRET 92220026600018, "
        "located at 9 rue des Colonnes, 75002 Paris, FRANCE  represented by Mathurin Blouin "
        '(CEO)  hereafter known as the '
    )
    pdf.inline_bold('"Customer"')
    pdf.inline_normal(" and")
    pdf.ln(10)

    # Party 2
    pdf.reset_x()
    pdf.inline_normal("(2) ")
    pdf.inline_bold(name)
    pdf.inline_normal(
        f" a {entity} located in {address}, "
        f'Operating as {alias} hereafter known as the '
    )
    pdf.inline_bold('"Affiliate"')
    pdf.ln(10)

    # Whereas
    pdf.section_title("Whereas:")
    pdf.body(
        "Now therefore, in consideration of the foregoing, and the mutual promises herein contained, "
        "the parties hereby agree as follows:"
    )

    # Description of Services
    pdf.section_title("Description of Services")
    pdf.body(
        'The Affiliate shall market, promote, and direct potential customers to the products and/or '
        'services (the "Services") of the Customer using specific URLs provided by the Customer. '
        'The Affiliate will use its best efforts to actively and effectively advertise, market and promote '
        'the Services as widely and aggressively as possible.'
    )

    if no_deliverables:
        pdf.body(
            "There are no minimum content deliverables required under this Agreement. The Affiliate "
            "shall promote the Services at its own discretion and pace."
        )
    else:
        deliverables_text = "Additionally, the Affiliate commits to delivering services outlined below:\n"
        for d in deliverables:
            deliverables_text += f"   - {d}\n"
        pdf.body(deliverables_text.rstrip())

    pdf.body(
        "The Affiliate must at all times incorporate Customer mentions and use its unique affiliate "
        "tracking link into all publications. All content must be new and unpublished. The Affiliate "
        "further undertakes not to remove these publications from their profiles or social channels for "
        "a minimum of one year, barring force majeure or professional activity abandonment. The "
        "Affiliate also agrees to maximum one (1) round of edits and republish within seven (7) days "
        "of publishing if the content falls short of the Agreement or adversely affects the Customer's "
        "image. Any failure to comply with the above can lead to Agreement breach and impact "
        "payments."
    )

    # Commission
    pdf.section_title("Commission")
    pdf.body(
        'The Customer shall pay the Affiliate a commission based on the "Net Revenue" generated '
        "from new customers directed by the Affiliate's efforts. The \"Net Revenue\" shall be defined as: "
        "the monthly purchases by customers directed by the Affiliate made on the Primary Market, "
        "less any chargebacks (credit card refunds), secondary sales (user-to-users), credits given to "
        "customers, processing fees, and sales tax. A cap will be applied to the \"Net Revenue\" "
        f"calculation, excluding revenue from users after {revenue_cap} of their account creation on the MFL "
        "platform."
    )

    pdf.body(
        "The commission rate will be a percentage of Net Revenue. This percentage will be defined "
        'each month based on the number of new paying users and brought by the Affiliate ("New '
        "Users\"), as shown in Table 1 below."
    )

    # Commission table
    if commission_tiers is None:
        commission_tiers = [("0", "5%"), ("1-2", "10%"), ("3-5", "12%"), ("6-20", "15%"), ("21+", "20%")]
    pdf.reset_x()
    pdf.set_font("Helvetica", "B", 10)
    col_w = 80
    pdf.cell(col_w, 8, "New Users", border=1, align="C")
    pdf.cell(col_w, 8, "Percentage of Net Revenue", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for nu, pct in commission_tiers:
        pdf.cell(col_w, 7, nu, border=1, align="C")
        pdf.cell(col_w, 7, pct, border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Table 1", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.body(
        "Commission will not be paid on sales taxes, duties, or any other charges related to the sale "
        "of the Services. No commission shall be payable for any transactions or activity occurring "
        "after the expiration or termination of this contract."
    )

    # Minimum Guarantee
    if no_guarantee:
        pdf.section_title("Minimum Guarantee Commission")
        guarantee_text = (
            "There is no minimum guarantee commission under this Agreement. The Affiliate's "
            "compensation shall consist solely of the commission as defined in the Commission section above."
        )
        if pack_bonus:
            guarantee_text += (
                f"\n\nAdditionally, the Affiliate will receive {pack_bonus}."
            )
        pdf.body(guarantee_text)
    else:
        pdf.section_title("Minimum Guarantee Commission")
        guarantee_text = (
            f"The Affiliate will be guaranteed a minimum commission of {guarantee} during the "
            "duration of this contract. In the event the Affiliate is eligible for a partial month of commission "
            "(e.g., if the contract begins or ends mid-month), the guaranteed commission will be prorated "
            "based on the number of days in that month."
        )
        if pack_bonus:
            guarantee_text += (
                f"\n\nAdditionally, the Affiliate will receive {pack_bonus}."
            )
        pdf.body(guarantee_text)

    # Welcome Bonus (optional)
    if welcome_bonus:
        pdf.section_title("Welcome Bonus")
        reason_text = (
            welcome_bonus_reason
            if welcome_bonus_reason
            else "This Welcome Bonus is provided as a goodwill gesture to support the Affiliate's content creation efforts. "
                 "It shall not be considered an advance on future commissions nor a recurring payment, "
                 "and shall not create any precedent for future compensation."
        )
        pdf.body(
            f"In addition to the Minimum Guarantee Commission, the Customer shall grant the Affiliate "
            f"a one-time Welcome Bonus in the amount of {welcome_bonus}.\n\n"
            f"{reason_text}"
        )

    # Duration
    pdf.section_title("Duration of the Contract")
    if initial_term:
        pdf.body(
            f"This Agreement shall begin on {start_date}, for an initial term of {initial_term}. "
            "Upon expiration of the initial term, this Agreement shall automatically renew for "
            "successive one (1) month periods unless either party provides written notice of "
            "non-renewal at least one (1) month prior to the end of the then-current term. "
            "The Agreement may also be amended or updated upon mutual agreement via email."
        )
    else:
        pdf.body(
            f"This Agreement shall begin on {start_date}, and shall remain in effect indefinitely. "
            "Either party may terminate this Agreement at any time by providing one month's written "
            "notice to the other party. The Agreement may also be amended or updated upon mutual "
            "agreement via email."
        )

    # Payment Terms
    pdf.section_title("Payment Terms and Schedule")
    payment_text = (
        "The commission will be paid on a monthly basis, within 30 days following the reception of the "
        "Affiliate invoice. The Affiliate shall receive a monthly report detailing the Net Revenue and "
        "calculation of the commission."
    )
    if payment_threshold:
        payment_text += (
            f"\n\nA minimum threshold of {payment_threshold} in accrued commissions must be reached "
            "before any payment is issued. If the accrued commission does not meet this threshold at the "
            "end of a given month, the amount will be carried over to the following month(s) until the "
            "threshold is met."
        )
    pdf.body(payment_text)

    # Terms and Conditions reference
    pdf.section_title("Terms and Conditions")
    pdf.body(
        "This Affiliate Contract is governed by the terms and conditions provided here and in "
        "Attachment A, attached hereto."
    )

    pdf.body(
        "IN WITNESS WHEREOF, by their respective signatures below, the parties have caused the "
        "Contract, inclusive of Attachment A, to be duly executed and effective as of the Effective Date."
    )

    pdf.sig_block(name)

    # ===================== ATTACHMENT A =====================
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.ln(10)
    pdf.multi_cell(w=0, h=12, text="Attachment A", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(w=0, h=8, text="Affiliate Contract Terms and Conditions", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 1. IP Rights
    pdf.chapter_title("1. Intellectual Property Rights")

    pdf.section_title("Retained rights")
    pdf.body(
        "Each party will retain all right, title, and interest in and to its own Pre-Existing Intellectual "
        "Property irrespective of any disclosure of such Pre Existing Intellectual Property to the other "
        "party, subject to any licenses granted herein."
    )

    pdf.section_title("Pre-existing intellectual property")
    pdf.body(
        "Affiliate will not use any Affiliate or third party Pre-Existing Intellectual Property in connection "
        "with this Contract unless Affiliate has the right to use it for Customer's benefit. If Affiliate is "
        "not the owner of such Pre Existing Intellectual Property, Affiliate will obtain from the owner "
        "any rights as are necessary to enable Affiliate to comply with this Contract."
    )
    pdf.body(
        "Affiliate grants Customer a non exclusive, royalty free, worldwide, perpetual and irrevocable "
        "license in Affiliate and third party Pre Existing Intellectual Property, to the extent such Pre-"
        "Existing Intellectual Property is incorporated into any Deliverable, with the license including "
        "the right to make, have made, sell, use, reproduce, modify, adapt, display, distribute, make "
        "other versions of and disclose the property and to sublicense others to do these things."
    )
    pdf.body(
        "Affiliate will not incorporate any materials from a third party, including Open Source or "
        "freeware, into any Deliverable unless (i) Affiliate clearly identifies the specific elements of the "
        "Deliverable to contain third party materials, (ii) Affiliate identifies the corresponding third party "
        "licenses and any restrictions on use thereof, and (ii) approval is given by Customer in writing."
    )
    pdf.body(
        "Affiliate represents, warrants and covenants that Affiliate has complied and shall continue to "
        "comply with all third party licenses (including all open source licenses) associated with any "
        "software components that will be included in the Deliverables or any other materials supplied "
        "by Affiliate."
    )
    pdf.body(
        "Affiliate shall indemnify Customer against any losses and liability incurred by Customer due "
        "to failure of Affiliate to meet any of the requirements in any of the third party licenses."
    )

    pdf.section_title("Ownership of deliverables")
    pdf.body(
        "Subject to Affiliate and third party rights in Pre Existing Intellectual Property, all Deliverables, "
        "whether complete or in progress, and all Intellectual Property Rights related thereto shall "
        "belong to Customer, and Affiliate hereby assigns such rights to Customer. Affiliate shall "
        "deliver all produced content (including but not limited to videos, code, and images) to the "
        "Customer in a downloadable and accessible format."
    )
    pdf.body(
        "Affiliate agrees that Customer will own all patents, inventor's certificates, utility models or "
        "other rights, copyrights or trade secrets covering the Deliverables and will have full rights to "
        "use the Deliverables without claim on the part of Affiliate for additional compensation and "
        "without challenge, opposition or interference by Affiliate and Affiliate will, and will cause each "
        "of its Personnel to, waive their respective moral rights therein."
    )
    pdf.body(
        "Affiliate will sign any necessary documents and will otherwise assist Customer in securing, "
        "maintaining and defending copyrights or other rights to protect the Deliverables in any country."
    )

    pdf.section_title("No rights to customer intellectual property")
    pdf.body(
        "Except for the limited license to use materials provided by Customer as may be necessary in "
        "order for Affiliate to perform Services under this Contract, Affiliate is granted no right, title, or "
        "interest in any Customer Intellectual Property."
    )

    # 2. Confidentiality
    pdf.chapter_title("2. Confidentiality")

    pdf.section_title("Confidential information")
    pdf.body(
        'For purposes of this Contract, "Confidential Information" shall mean information or material '
        'proprietary to a Party or designated as confidential by such Party (the "Disclosing Party"), as '
        'well as information about which a Party (the "Receiving Party") obtains knowledge or access, '
        "through or as a result of this Contract (including information conceived, originated, "
        "discovered or developed in whole or in part by Affiliate hereunder)."
    )

    pdf.body("Confidential Information does not include:", space_after=False)
    pdf.body(
        "a) information that is or becomes publicly known without restriction and without breach of this "
        "Contract or that is generally employed by the trade at or after the time the Receiving Party "
        "first learns of such information;", space_after=False
    )
    pdf.body(
        "b) generic information or knowledge which the Receiving Party would have learned in the "
        "course of similar employment or work elsewhere in the trade;", space_after=False
    )
    pdf.body(
        "c) information the Receiving Party lawfully receives from a third party without restriction on "
        "disclosure and without breach of a nondisclosure obligation;", space_after=False
    )
    pdf.body(
        "d) information the Receiving Party rightfully knew prior to receiving such information from the "
        "Disclosing Party to the extent such knowledge was not subject to restrictions on further "
        "disclosure;", space_after=False
    )
    pdf.body(
        "or (e) information the Receiving Party develops independent of any information originating "
        "from the Disclosing Party."
    )

    pdf.section_title("Customer confidential information")
    pdf.body(
        "The following constitute Confidential Information of Customer and should not be disclosed to "
        "third parties: the Deliverables, discoveries, ideas, concepts, software in various states of "
        "development, designs, drawings, specifications, techniques, models, data, source code, "
        "source files and documentation, object code, documentation, diagrams, flow charts, "
        'research, development, processes, procedures, "know-how", marketing techniques and '
        "materials, marketing and development plans, customer names and other information related "
        "to customers, price lists, pricing policies and financial information, this Contract and the "
        "existence of this Contract, and any work assignments authorized or issued under this Contract."
    )
    pdf.body(
        'Affiliate will not use Customer\'s name, likeness, or logo (Customer\'s "Identity"), without '
        "Customer's prior written consent, to include use or reference to Customer's Identity, directly "
        "or indirectly, in conjunction with any other clients or potential clients, any client lists, "
        "advertisements, news releases or releases to any professional or trade publications."
    )

    pdf.section_title("Non-Disclosure")
    pdf.body(
        "The Parties hereby agree that during the term hereof and at all times thereafter, and except "
        "as specifically permitted herein or in a separate writing signed by the Disclosing Party, the "
        "Receiving Party shall not use, commercialize or disclose Confidential Information to any "
        "person or entity."
    )
    pdf.body(
        "Upon termination, or at any time upon the request of the Disclosing Party, the Receiving "
        "Party shall return to the Disclosing Party all Confidential Information, including all notes, data, "
        "reference materials, sketches, drawings, memorandums, documentations and records which "
        "in any way incorporate Confidential Information."
    )

    pdf.section_title("Right to disclose")
    pdf.body(
        "With respect to any information, knowledge, or data disclosed to Customer by the Affiliate, "
        "the Affiliate warrants that the Affiliate has full and unrestricted right to disclose the same "
        "without incurring legal liability to others, and that Customer shall have full and unrestricted "
        "right to use and publish the same as it may see fit."
    )
    pdf.body(
        "Any restrictions on Customer's use of any information, knowledge, or data disclosed by "
        "Affiliate must be made known to Customer as soon as practicable and in any event agreed "
        "upon before the start of any work."
    )

    # 3. Conflict of Interest
    pdf.chapter_title("3. Conflict of Interest")
    pdf.body(
        "Affiliate represents that its execution and performance of this Contract does not conflict with "
        "or breach any contractual, fiduciary or other duty or obligation to which Affiliate is bound."
    )
    if not no_conflict_clause:
        pdf.body(
            "Affiliate shall not accept any work from Customer or work from any other business "
            "organizations or entities which would create an actual or potential conflict of interest for the "
            "Affiliate or which is detrimental to Customer's business interests."
        )

    # 4. Termination
    pdf.chapter_title("4. Termination")
    pdf.section_title("Rights to Terminate")
    pdf.body(
        "1. Customer may terminate this Contract and/or any open projects immediately for cause if "
        "the Affiliate fails to perform any of its obligations under this Contract or if Affiliate breaches "
        "any of the warranties provided herein and fails to correct such failure or breach to "
        "Customer's reasonable satisfaction within ten (10) calendar days (unless extended by "
        "Customer) following notice by Customer. Customer shall be entitled to seek and obtain all "
        "remedies available to it in law or in equity."
    )
    pdf.body(
        "2. Upon termination of any project or work given Affiliate hereunder, Affiliate will immediately "
        "provide Customer with any and all work in progress or completed prior to the termination "
        "date. As Customer's sole obligation to Affiliate resulting from such termination, Customer will "
        "pay Affiliate an equitable amount as determined by Customer for the partially completed work "
        "in progress and the agreed to price for the completed Services and/or Deliverables provided "
        "and accepted prior to the date of termination."
    )
    pdf.body(
        "3. Upon termination or expiration of this Contract or a project performed by Affiliate "
        "hereunder, whichever occurs first, Affiliate shall promptly return to Customer all materials and "
        "or tools provided by Customer under this Contract and all Confidential Information provided "
        "by Customer to Affiliate."
    )
    pdf.body(
        "4. Any provision or clause in this Contract that, by its language or context, implies its survival "
        "shall survive any termination or expiration of this Contract."
    )

    # 5. Warranties
    pdf.chapter_title("5. Warranties")
    pdf.body("Affiliate warrants that:", space_after=False)
    pdf.body(
        "1. the Services and Deliverables are original and do not infringe upon any third party's "
        "patents, trademarks, trade secrets, copyrights or other proprietary rights,", space_after=False
    )
    pdf.body(
        "2. it will perform the Services hereunder in a professional and workmanlike manner,", space_after=False
    )
    pdf.body(
        "3. the Deliverables Affiliate provides to Customer are new, of acceptable quality free from "
        "defects in material and workmanship and will meet the requirements and conform with any "
        "specifications agreed between the parties,", space_after=False
    )
    pdf.body(
        "4. it has all necessary permits and is authorized to do business in all jurisdictions where "
        "Services are to be performed,", space_after=False
    )
    pdf.body(
        "5. it will comply with all applicable federal and other jurisdictional laws in performing the "
        "Services,", space_after=False
    )
    pdf.body(
        "6. it has all rights to enter into this Contract and there are no impediments to Affiliate's "
        "execution of this Contract or Affiliate's performance of Services hereunder."
    )

    # 6. Limitation of Liability
    pdf.chapter_title("6. Limitation of Liability")
    pdf.body(
        "Except as set forth in this section below, in no event will either party be liable for any special, "
        "indirect, incidental, or consequential damages nor for loss of data, profits or revenue, cost of "
        "capital or downtime costs, nor for any exemplary or punitive damages, arising from any claim "
        "or action, incidental or collateral to, or directly or indirectly related to or in any way connected "
        "with, the subject matter of the agreement, whether such damages are based on contract, "
        "tort, statute, implied duties or obligations, or other legal theory, even if advised of the "
        "possibility of such damages."
    )
    pdf.body(
        "Notwithstanding the foregoing, any purported limitation or waiver of liability shall not apply to "
        "the contractor's obligation under the indemnification or confidential information sections of "
        "this agreement or either party's liability to the other for personal injury, death, or physical "
        "damage to property claims."
    )

    # 7. Inspection and Acceptance
    pdf.chapter_title("7. Inspection and Acceptance")
    pdf.section_title("Non-conforming services and deliverables")
    pdf.body(
        "If any of the Services performed or Deliverables delivered do not conform to specified "
        "requirements, Customer may require the Affiliate to perform the Services again or replace or "
        "repair the non conforming Deliverables in order to bring them into full conformity with the "
        "requirements, at Affiliate's sole cost and expense."
    )
    pdf.body(
        "When the defects in Services and/or Deliverables cannot be corrected by re-performance, "
        "Customer may: (a) require Affiliate to take necessary action, at Affiliate's own cost and "
        "expense, to ensure that future performance conforms to the requirements and/or (b) reduce "
        "any price payable under the applicable project to reflect the reduced value of the Services "
        "performed and/or Deliverables delivered by Affiliate and accepted by Customer."
    )
    pdf.body(
        "If Affiliate fails to promptly conform the Services and/or Deliverables to defined requirements "
        "or specifications, or take action deemed by Customer to be sufficient to ensure future "
        "performance of the project in full conformity with such requirements, Customer may (a) by "
        "contract or otherwise, perform the services or subcontract to another Affiliate to perform the "
        "Services and reduce any price payable by an amount that is equitable under the "
        "circumstances and charge the difference in re-procurement costs back to Affiliate and/or (b) "
        "terminate the project and/or this Contract for default."
    )

    # 8. Insurance
    pdf.chapter_title("8. Insurance")
    pdf.body(
        "Affiliate shall maintain adequate insurance coverage and minimum coverage limits for its "
        "business as required by any applicable law or regulation, including Workers' Compensation "
        "insurance as required by any applicable law or regulation, or otherwise as determined by "
        "Affiliate in its reasonable discretion. Affiliate's lack of insurance coverage shall limit any "
        "liability Affiliate may have under this Contract."
    )

    # 10. Miscellaneous
    pdf.chapter_title("10. Miscellaneous")

    pdf.section_title("Assignment")
    pdf.body(
        "Affiliate shall not assign any rights of this Contract or any other written instrument related to "
        "Services and/or Deliverables provided under this Contract, and no assignment shall be "
        "binding without the prior written consent of Customer. Subject to the foregoing, this Contract "
        "will be binding upon the Parties' heirs, executors, successors and assigns."
    )

    pdf.section_title("Governing law")
    pdf.body(
        "The Parties shall make a good-faith effort to amicably settle by mutual agreement any "
        "dispute that may arise between them under this Contract. The foregoing requirement will not "
        "preclude either Party from seeking injunctive relief as it deems necessary to protect its own "
        "interests. This Contract will be construed and enforced in accordance with the laws of the "
        "State of France, excluding its choice of law rules."
    )

    pdf.section_title("Severability")
    pdf.body(
        "The Parties recognize the uncertainty of the law with respect to certain provisions of this "
        "Contract and expressly stipulate that this Contract will be construed in a manner that renders "
        "its provisions valid and enforceable to the maximum extent possible under applicable law."
    )
    pdf.body(
        "To the extent that any provisions of this Contract are determined by a court of competent "
        "jurisdiction to be invalid or unenforceable, such provisions will be deleted from this Contract "
        "or modified so as to make them enforceable and the validity and enforceability of the "
        "remainder of such provisions and of this Contract will be unaffected."
    )

    pdf.section_title("Independent contractor")
    pdf.body(
        "Nothing contained in this Contract shall create an employer and employee relationship, a "
        "master and servant relationship, or a principal and agent relationship between Affiliate and "
        "Customer. Customer and Affiliate agree that Affiliate is, and at all times during this Contract "
        "shall remain, an independent contractor."
    )

    pdf.section_title("Force majeure")
    pdf.body(
        "Neither Party shall be liable for any failure to perform under this Contract when such failure is "
        "due to causes beyond that Party's reasonable control, including, but not limited to, acts of "
        "state or governmental authorities, acts of terrorism, natural catastrophe, fire, storm, flood, "
        "earthquakes, accident, and prolonged shortage of energy."
    )
    pdf.body(
        "In the event of such delay the date of delivery or time for completion will be extended by a "
        "period of time reasonably necessary by both Affiliate and Customer. If the delay remains in "
        "effect for a period in excess of thirty days, Customer may terminate this Contract immediately "
        "upon written notice to Affiliate."
    )

    pdf.section_title("Entire contract")
    pdf.body(
        "This document and all attached or incorporated documents contains the entire agreement "
        "between the Parties and supersedes any previous understanding, commitments or "
        "agreements, oral or written. Further, this Contract may not be modified, changed, or "
        "otherwise altered in any respect except by a written agreement signed by both Parties."
    )

    pdf.sig_block(name)

    # Save
    pdf.output(output_path)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MFL Affiliate Contract PDF")
    parser.add_argument("--name", default="XXXXX", help="Affiliate legal name")
    parser.add_argument("--entity", default="XXXXX", help="Business entity type (e.g., Sole Trader)")
    parser.add_argument("--address", default="XXXXX", help="Affiliate legal address")
    parser.add_argument("--alias", default="XXXXX", help="Operating name / creator alias")
    parser.add_argument("--start-date", default="XXXXX", help="Contract start date (e.g., March 1st, 2026)")
    parser.add_argument("--guarantee", default="XXXXX", help="Minimum guarantee (e.g., 200 EUR/month)")
    parser.add_argument("--deliverables", default=None, help="Pipe-separated deliverables list")
    parser.add_argument("--output", default=None, help="Output PDF path")
    parser.add_argument("--no-conflict-clause", action="store_true", help="Remove competition restriction from Conflict of Interest section")
    parser.add_argument("--initial-term", default=None, help="Initial contract term (e.g., '3 months'). Auto-renews monthly after.")
    parser.add_argument("--pack-bonus", default=None, help="Pack bonus text to add to guarantee section")
    parser.add_argument("--welcome-bonus", default=None, help="One-time welcome bonus amount (e.g., '150 EUR')")
    parser.add_argument("--welcome-bonus-reason", default=None, help="Custom reason text for the welcome bonus clause")
    parser.add_argument("--revenue-cap", default="one year", help="Revenue cap duration per user (e.g., 'two years')")
    parser.add_argument("--commission-tiers", default=None, help="Pipe-separated commission tiers (e.g., '0:5%%|1-10:10%%|11-20:12%%|21+:15%%')")
    parser.add_argument("--representative", default=None, help="Representative name/title for cover page (e.g., 'Craig Douglas, Director')")
    parser.add_argument("--payment-threshold", default=None, help="Minimum payment threshold (e.g., '100 USD')")
    args = parser.parse_args()

    deliverables = args.deliverables.split("|") if args.deliverables else None
    commission_tiers = None
    if args.commission_tiers:
        commission_tiers = []
        for tier in args.commission_tiers.split("|"):
            users, pct = tier.split(":")
            commission_tiers.append((users.strip(), pct.strip()))

    path = generate_contract(
        name=args.name,
        entity=args.entity,
        address=args.address,
        alias=args.alias,
        start_date=args.start_date,
        guarantee=args.guarantee,
        deliverables=deliverables,
        output_path=args.output,
        no_conflict_clause=args.no_conflict_clause,
        initial_term=args.initial_term,
        pack_bonus=args.pack_bonus,
        welcome_bonus=args.welcome_bonus,
        welcome_bonus_reason=args.welcome_bonus_reason,
        revenue_cap=args.revenue_cap,
        commission_tiers=commission_tiers,
        representative=args.representative,
        payment_threshold=args.payment_threshold,
    )
    print(f"Contract saved to: {path}")
