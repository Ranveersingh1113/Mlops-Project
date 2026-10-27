"""Create a vector poster and A3 PDF. No generated imagery or raster text."""
from html import escape
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parent
W, H = 1000, 1414
NAVY, TEAL, AMBER = "#15283E", "#087F8C", "#EAA33B"
INK, MUTED, PAPER = "#24384D", "#51677B", "#F7FAFC"
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="420mm" viewBox="0 0 {W} {H}">']
c = Canvas(str(ROOT / "delhi-aqi-poster.pdf"), pagesize=A3)
c.setTitle("Delhi AQI Forecasting - MLOps Project Poster")
c.setAuthor("MLOps Project")
c.scale(A3[0] / W, A3[1] / H)


def box(x, y, w, h, fill, radius=12, stroke=None):
    c.setFillColor(HexColor(fill))
    c.setStrokeColor(HexColor(stroke or fill))
    c.roundRect(x, H - y - h, w, h, radius, fill=1, stroke=int(stroke is not None))
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke or fill}"/>')


def text(x, y, value, size=15, color=INK, bold=False):
    font = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(font, size)
    c.setFillColor(HexColor(color))
    c.drawString(x, H - y, value)
    svg.append(f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')


def paragraph(x, y, value, width, size=15, color=INK, bold=False, leading=None):
    lines = simpleSplit(value, "Helvetica-Bold" if bold else "Helvetica", size, width)
    for i, line in enumerate(lines):
        text(x, y + i * (leading or size * 1.4), line, size, color, bold)
    return y + len(lines) * (leading or size * 1.4)


def line(x1, y1, x2, y2, color=TEAL, width=2):
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(width)
    c.line(x1, H - y1, x2, H - y2)
    svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')


def arrow(x1, y1, x2, y2, color=TEAL):
    line(x1, y1, x2, y2, color)
    if x1 == x2:
        direction = 1 if y2 > y1 else -1
        line(x2, y2, x2 - 5, y2 - direction * 7, color)
        line(x2, y2, x2 + 5, y2 - direction * 7, color)
    else:
        direction = 1 if x2 > x1 else -1
        line(x2, y2, x2 - direction * 7, y2 - 5, color)
        line(x2, y2, x2 - direction * 7, y2 + 5, color)


def circle(x, y, radius, color):
    c.setFillColor(HexColor(color))
    c.circle(x, H - y, radius, fill=1, stroke=0)
    svg.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}"/>')


def section(y, number, title, label):
    box(44, y - 27, 44, 38, TEAL, 8)
    text(53, y, number, 21, "#FFFFFF", True)
    text(103, y, title, 23, NAVY, True)
    if label:
        text(956 - stringWidth(label, "Helvetica", 12), y - 2, label, 12, MUTED)


def node(x, y, number, title, caption):
    box(x, y, 168, 86, "#E7F3F5")
    text(x + 13, y + 22, number, 12, TEAL, True)
    paragraph(x + 13, y + 43, title, 145, 16, NAVY, True, 18)
    if caption:
        paragraph(x + 13, y + 72, caption, 145, 11, MUTED, leading=13)


box(0, 0, W, H, PAPER, 0)
box(0, 0, W, 193, NAVY, 0)
text(44, 42, "MLOps PROJECT  /  INDIA  /  DESIGN POSTER", 13, "#9EE0E1", True)
text(44, 101, "DELHI AQI", 53, "#FFFFFF", True)
text(44, 157, "FORECASTING", 53, "#FFFFFF", True)
text(635, 85, "Tomorrow's air quality.", 22, "#FFFFFF", True)
paragraph(635, 119, "A reproducible forecast, monitored after deployment.", 300, 18, "#C6DCE8")

box(44, 214, 442, 116, "#FFFFFF", stroke="#D8E4EB")
text(62, 240, "PRACTICAL PURPOSE", 13, TEAL, True)
paragraph(62, 269, "Predict next-day city AQI to support awareness and planning around pollution trends.", 400, 19, NAVY, True, 24)
box(504, 214, 452, 116, "#FFFFFF", stroke="#D8E4EB")
text(522, 240, "REAL DATA / EASY ACCESS", 13, TEAL, True)
text(522, 270, "3,143 daily Delhi records", 23, NAVY, True)
text(522, 296, "May 2015 - Dec 2023 / CPCB bulletin compilation", 14, MUTED)
text(522, 316, "Public CSV / no account or API key", 14, MUTED)

section(371, "01", "ML PIPELINE + CI/CD", "Poster criterion 1 / CO4")
first = [("01", "CPCB CSV", "Version + validate"), ("02", "Lag features", "Seven prior AQI days"),
         ("03", "Train + compare", "Persistence vs forest"), ("04", "MLflow tracking", "Params + run metrics"),
         ("05", "Quality gate", "Chronological holdout")]
second = [("06", "GitHub Actions", "Checks on commits"), ("07", "Docker build", "Pinned dependencies"),
          ("08", "Artifact Registry", "Versioned images"), ("09", "Cloud Run API", "Candidate + smoke test"),
          ("10", "Dashboard", "Forecast + model ID")]
for row, y in [(first, 399), (second, 520)]:
    for i, (number, title, caption) in enumerate(row):
        x = 44 + i * 186
        node(x, y, number, title, caption)
        if i < 4:
            arrow(x + 169, y + 43, x + 183, y + 43)
line(872, 485, 872, 502)
line(872, 502, 128, 502)
arrow(128, 502, 128, 519)
box(44, 622, 912, 50, "#D8EEEE", 9)
text(62, 643, "Cloud Storage: versioned data + experiment artifacts. Promotion: checks + recorded approval.", 15, NAVY, True)
text(62, 663, "Time order preserved / tune on validation / final test reported separately / no future AQI features", 13, MUTED)

section(721, "02", "DEPLOYMENT STRATEGY", "Docker + managed scaling")
deploy = [(44, "SCALE", "Stateless FastAPI on Cloud Run. Scale to zero; service cap 3; tagged candidates add capacity."),
          (353, "RELEASE + ROLLBACK", "Deploy candidate revision, smoke-test, then approve traffic switch. Restore prior revision if needed."),
          (662, "DEPLOYMENT CHALLENGES", "Cold starts: small image. Model mismatch: pinned digest. Access: OIDC and least-privilege IAM.")]
for x, title, description in deploy:
    box(x, 750, 294, 136, "#FFFFFF", stroke="#D8E4EB")
    text(x + 16, 777, title, 14, TEAL, True)
    paragraph(x + 16, 805, description, 260, 16, INK, leading=21)

section(934, "03", "MONITOR + RETRAIN", "CO3 / feedback after actuals arrive")
monitor = [("Forecast", "Log model version"), ("Actual AQI", "Join by target date"),
           ("Error + drift", "MAE / input shift"), ("Review candidate", "Retrain + rerun gate")]
for i, (title, caption) in enumerate(monitor):
    x = 44 + i * 232
    box(x, 960, 216, 75, "#E7F3F5")
    text(x + 14, 990, title, 18, NAVY, True)
    text(x + 14, 1017, caption, 14, MUTED)
    if i < 3:
        arrow(x + 217, 997, x + 229, 997)
box(44, 1048, 912, 40, "#FFF0D6", 8)
text(60, 1074, "Cloud Logging: latency + failures. Drift prompts review; models never auto-promote.", 16, NAVY, True)

section(1137, "04", "GOVERNANCE + RESPONSIBLE AI", "Poster criterion 2 / CO4")
governance = [
    ("01", "VERSIONING", "Data SHA-256, Git SHA, MLflow run ID and container digest."),
    ("02", "AUDIT TRAIL", "Metrics, timestamp, named approver and deployed revision recorded."),
    ("03", "COMPLIANCE", "Public aggregate data; source attribution; IAM; log retention policy."),
    ("04", "BIAS MITIGATION", "Report seasonal errors; inspect extreme-AQI failures; disclose coverage gaps."),
]
for i, (number, title, description) in enumerate(governance):
    x = 44 + i * 232
    box(x, 1164, 216, 131, "#FFFFFF", stroke="#D8E4EB")
    box(x + 14, 1178, 28, 28, TEAL, 5)
    if i == 0:  # Version graph.
        line(x + 23, 1184, x + 23, 1200, "#FFFFFF")
        line(x + 23, 1194, x + 34, 1188, "#FFFFFF")
        for cx, cy in [(x + 23, 1184), (x + 23, 1200), (x + 34, 1188)]:
            circle(cx, cy, 2.8, "#FFFFFF")
    elif i == 1:  # Audit checklist.
        for cy in (1185, 1192, 1199):
            line(x + 25, cy, x + 36, cy, "#FFFFFF", 1.8)
            circle(x + 20, cy, 1.5, "#FFFFFF")
    elif i == 2:  # Governance shield.
        points = [(x + 28, 1183), (x + 37, 1187), (x + 35, 1196),
                  (x + 28, 1202), (x + 21, 1196), (x + 19, 1187), (x + 28, 1183)]
        for a, b in zip(points, points[1:]):
            line(*a, *b, "#FFFFFF", 1.8)
        line(x + 24, 1192, x + 27, 1195, "#FFFFFF", 1.6)
        line(x + 27, 1195, x + 33, 1189, "#FFFFFF", 1.6)
    else:  # Compare cohort/season errors.
        for cx, cy in [(x + 20, 1191), (x + 26, 1184), (x + 32, 1189), (x + 38, 1186)]:
            line(cx, 1200, cx, cy, "#FFFFFF", 3)
    text(x + 50, 1198, title, 13, TEAL, True)
    paragraph(x + 14, 1230, description, 186, 15, INK, leading=20)

line(44, 1320, 956, 1320, "#CCDCE5", 1)
text(44, 1343, "DEMO: historical replay > forecast > inject drift > review > deploy > rollback", 15, NAVY, True)
text(44, 1366, "Scope: city-level historical backtesting. Live forecasts need fresh inputs; no health or accuracy guarantees.", 12, MUTED)
text(44, 1387, "Data: UrbanEmissions / CPCB bulletins (Zenodo 11146316). Architecture: Cloud Run + MLflow documentation.", 11, MUTED)

c.showPage()
c.save()
svg.append("</svg>")
(ROOT / "delhi-aqi-poster.svg").write_text("\n".join(svg), encoding="utf-8")
print("Created editable SVG and vector A3 PDF")
