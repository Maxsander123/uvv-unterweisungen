"""PDF-Nachweis: Seite 1 Bestätigung mit QR-Code, ab Seite 2 die Inhalte der Unterweisung."""
import io

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                                ListFlowable, ListItem, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

RED = colors.HexColor("#BA0000")
DARK = colors.HexColor("#1F2328")
GREY = colors.HexColor("#5A6470")
LIGHT = colors.HexColor("#F3F3F4")
GOLD = colors.HexColor("#F5C400")
GREEN = colors.HexColor("#2E7D32")

W, H = A4
M = 20 * mm
HEADER_H = 34 * mm

S = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=DARK, spaceAfter=2 * mm),
    "h1c": ParagraphStyle("h1c", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=DARK, spaceAfter=1 * mm),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=12, leading=16, textColor=GREY, spaceAfter=8 * mm),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=DARK, alignment=TA_LEFT),
    "label": ParagraphStyle("label", fontName="Helvetica", fontSize=9, leading=12, textColor=GREY),
    "value": ParagraphStyle("value", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=DARK),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=RED, spaceBefore=2 * mm, spaceAfter=0.8 * mm),
    "item": ParagraphStyle("item", fontName="Helvetica", fontSize=9.5, leading=12, textColor=DARK),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=GREY),
    "qr": ParagraphStyle("qr", fontName="Helvetica", fontSize=8.5, leading=11, textColor=GREY, alignment=1),
}


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _qr_png(url):
    img = qrcode.make(url, box_size=10, border=1,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _spaced(text):
    """Kurze Titel gesperrt setzen wie im Banner („F E U E R W E H R“)."""
    text = text.upper()
    return " ".join(text) if len(text) <= 12 and " " not in text else text


def build_certificate(r, verify_url, t, cfg, logo_path, primary,
                      signature=None, signed_at=None):
    """t: Stand der Unterweisung (title, short_name, description, subtitle, legal, content).
    cfg: Einstellungen (org_name, brand_top, brand_bottom, sign_place)."""
    buf = io.BytesIO()
    topic, content = t["title"], t["content"]
    org_name, sign_place = cfg["org_name"], cfg["sign_place"]
    red = colors.HexColor(primary)
    logo_ratio = None
    if logo_path:
        try:
            from PIL import Image as PILImage
            with PILImage.open(logo_path) as im:
                logo_ratio = im.width / im.height
        except Exception:  # Logo nicht lesbar – PDF ohne Logo erzeugen
            logo_ratio = None

    def page_deco(c, doc):
        c.saveState()
        # Kopfband im Feuerwehr-Rot
        c.setFillColor(red)
        c.rect(0, H - HEADER_H, W, HEADER_H, stroke=0, fill=1)
        tx = M
        if logo_ratio:
            logo_h = 26 * mm
            logo_w = min(logo_h * logo_ratio, 60 * mm)
            logo_h = logo_w / logo_ratio
            try:
                c.drawImage(logo_path, M, H - HEADER_H / 2 - logo_h / 2, width=logo_w, height=logo_h, mask="auto")
                tx = M + logo_w + 6 * mm
            except Exception:  # Logo fehlt oder ist nicht lesbar – PDF trotzdem erzeugen
                pass
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 19)
        c.drawString(tx, H - 16 * mm, _spaced(cfg["brand_top"]))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(tx, H - 23.5 * mm, cfg["brand_bottom"].upper())
        c.setFont("Helvetica", 9)
        c.drawRightString(W - M, H - 23.5 * mm, f"UVV-Unterweisung · {t['short_name']}")
        # Fußzeile
        c.setFillColor(GREY)
        c.setFont("Helvetica", 8)
        c.drawString(M, 12 * mm, f"{org_name} · Nachweis-ID {r['short_id']}")
        c.drawRightString(W - M, 12 * mm, f"Seite {doc.page}")
        c.restoreState()

    doc = BaseDocTemplate(buf, pagesize=A4, title=f"Nachweis {topic} – {r['name']}",
                          author=org_name, subject=topic)
    frame = Frame(M, 20 * mm, W - 2 * M, H - HEADER_H - 30 * mm, id="main",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=page_deco)])

    story = [
        Spacer(1, 4 * mm),
        Paragraph("Nachweis über die Unterweisung", S["h1"]),
    ]
    story.append(Paragraph(_esc(t["subtitle"]), S["sub"]) if t.get("subtitle") else Spacer(1, 6 * mm))

    def cell(label, value):
        return [Paragraph(label, S["label"]), Paragraph(_esc(value), S["value"])]

    info = Table([
        [cell("Name", r["name"]), cell("Datum der Unterweisung", r["datetime_str"])],
        [cell("Wissensüberprüfung", "bestanden"),
         cell("Gültig bis (nächste Unterweisung)", r["valid_str"])],
        [cell("Thema", t.get("description") or topic),
         cell("Nachweis-ID", r["short_id"])],
    ], colWidths=[(W - 2 * M) * 0.58, (W - 2 * M) * 0.42])
    info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.6, colors.white),
    ]))
    story += [info, Spacer(1, 8 * mm)]

    statement = (
        f"Hiermit wird bestätigt, dass <b>{_esc(r['name'])}</b> am {r['date_str']} an der "
        f"{_esc(topic)} ({_esc(org_name)}) teilgenommen hat. Die Inhalte "
        f"(siehe folgende Seiten) wurden zur Kenntnis genommen. Die anschließende "
        f"Wissensüberprüfung wurde erfolgreich bestanden."
    )
    qr_size = 38 * mm
    qr_block = [Image(_qr_png(verify_url), width=qr_size, height=qr_size),
                Spacer(1, 1.5 * mm),
                Paragraph("Scannen, um Datum und Gültigkeit online zu prüfen", S["qr"])]
    stmt = Table([[[Paragraph(statement, S["body"])], qr_block]],
                 colWidths=[W - 2 * M - qr_size - 10 * mm, qr_size + 10 * mm])
    stmt.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 8 * mm),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
    ]))
    story += [stmt, Spacer(1, 8 * mm)]

    sig_w = (W - 2 * M - 12 * mm) / 2
    sig_h = 20 * mm
    place_cell, sig_cell = "", ""
    if signature and signed_at:
        place_cell = Paragraph(_esc(f"{sign_place}, {signed_at:%d.%m.%Y}" if sign_place
                                    else f"{signed_at:%d.%m.%Y}"), S["value"])
        try:
            from PIL import Image as PILImage
            pil = PILImage.open(io.BytesIO(signature))
            ratio = pil.width / pil.height
            h = sig_h - 2 * mm
            w = min(sig_w, h * ratio)
            h = w / ratio
            sig_cell = Image(io.BytesIO(signature), width=w, height=h)
        except Exception:
            sig_cell = ""
    sig_label = "Unterschrift Teilnehmer/-in"
    if signature and signed_at:
        sig_label += f" (digital unterschrieben am {signed_at:%d.%m.%Y, %H:%M} Uhr)"
    sig = Table([[place_cell, "", sig_cell],
                 [Paragraph("Ort, Datum", S["small"]), "",
                  Paragraph(sig_label, S["small"])]],
                colWidths=[sig_w, 12 * mm, sig_w], rowHeights=[sig_h, None])
    sig.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.8, DARK),
        ("LINEABOVE", (2, 1), (2, 1), 0.8, DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1 * mm),
    ]))
    story += [sig, Spacer(1, 10 * mm)]
    if t.get("legal"):
        story += [Paragraph("Rechtliche Grundlagen: " + _esc(t["legal"]), S["small"]), Spacer(1, 2 * mm)]
    story += [
              Paragraph(f"Online-Prüfung: {_esc(verify_url)}", S["small"]),
              PageBreak(),
              Paragraph("Inhalte der Unterweisung", S["h1c"])]

    h2 = ParagraphStyle("h2t", parent=S["h2"], textColor=red)
    for heading, items in content:
        lst = ListFlowable(
            [ListItem(Paragraph(_esc(t), S["item"]), leftIndent=5 * mm) for t in items],
            bulletType="bullet", bulletColor=red, bulletFontSize=10, leftIndent=5 * mm, start="•")
        story.append(KeepTogether([Paragraph(_esc(heading), h2), lst]))

    doc.build(story)
    return buf.getvalue()
