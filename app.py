from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import logging
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Mapeo P/E promedio por sector (2025E)
SECTOR_PE = {
    "Technology":             30.2,
    "Financial Services":     18.0,
    "Consumer Cyclical":      27.2,
    "Communication Services": 19.6,
    "Industrials":            25.9,
    "Healthcare":             16.8,
    "Consumer Defensive":     20.1,
    "Energy":                 16.3,
    "Basic Materials":        23.6,
    "Real Estate":            15.3,
    "Utilities":              18.5,
}

def obtener_pe_sector(sector_name: str) -> float:
    """
    Dada la cadena de sector (por ejemplo "Technology"),
    construye el slug esperado por Yahoo (ms_technology),
    descarga la página de screener y extrae el PE Ratio (TTM).
    """
    slug = "ms_" + sector_name.lower().replace(" ", "_")
    url = f"https://finance.yahoo.com/screener/predefined/{slug}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=5)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    # Busca la celda de la primera fila que contenga "PE Ratio (TTM)"
    cell = soup.select_one("table tbody tr td[data-col1='PE Ratio (TTM)']")
    if not cell:
        return None
    text = cell.get_text().replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None

@app.route("/datos", methods=["GET"])
def datos():
    ticker = request.args.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Ticker no proporcionado"}), 400

    try:
        stock = yf.Ticker(ticker)
        info  = stock.info or {}

        sector = info.get("sector") or ""    # p.ej. "Technology"
        pe_sector = SECTOR_PE.get(sector)  # filtrado automático

        company_name = info.get("longName") or info.get("shortName") or ticker

        # ── Fundamental data ──────────────────────────────────────────
        shares_outstanding = info.get("sharesOutstanding")
        cash               = info.get("totalCash") or info.get("cashAndShortTermInvestments")
        short_debt         = info.get("shortTermDebt") or 0
        long_debt          = info.get("longTermDebt")  or 0
        debt               = info.get("totalDebt") or (short_debt + long_debt)

        # ── Safe cashflow ──────────────────────────────────────────────
        try:
            cf_df = stock.cashflow
            if cf_df is None or getattr(cf_df, "empty", False):
                cashflow = {}
            else:
                cashflow = cf_df
        except Exception:
            cashflow = {}

        # ── Price fallback ─────────────────────────────────────────────
        precio = info.get("currentPrice") or info.get("regularMarketPrice")

        # ── FCF ─────────────────────────────────────────────────────────
        fcf = info.get("freeCashflow")
        if fcf is None:
            try:
                op    = cashflow.get("Total Cash From Operating Activities", [None])[0]
                capex = cashflow.get("Capital Expenditures",           [None])[0]
                if op is not None and capex is not None:
                    fcf = op - capex
            except Exception:
                fcf = None

        # ── EPS & P/E ──────────────────────────────────────────────────
        eps = info.get("forwardEps") or info.get("epsTrailingTwelveMonths") or 0
        pe  = info.get("forwardPE")    or info.get("trailingPE")             or None

        # ── Market cap & EV/CFO ────────────────────────────────────────
        market_cap       = info.get("marketCap")
        enterprise_value = info.get("enterpriseValue")
        ev_cfo           = None
        if fcf and enterprise_value:
            try:
                ev_cfo = round(enterprise_value / fcf, 2)
            except Exception:
                ev_cfo = None

        # ── Analyst target ──────────────────────────────────────────────
        target_price = info.get("targetMeanPrice")

        # ── P/E del sector (scraping) ──────────────────────────────────
        sector = info.get("sector") or ""
        try:
            pe_sector = obtener_pe_sector(sector) if sector else None
        except Exception as e:
            app.logger.warning(f"No pude obtener PE sector para {sector}: {e}")
            pe_sector = None

        # ── Respuesta final ────────────────────────────────────────────
        response = {
            "ticker":            ticker,
            "companyName":       company_name,
            "sector":            sector,
            "precio":            precio,
            "fcf":               fcf,
            "wacc":              0.08,
            "g":                 0.02,
            "sharesOutstanding": shares_outstanding,
            "cash":              cash,
            "debt":              debt,
            "dividendo":         info.get("dividendRate"),
            "eps":               eps,
            "pe":                pe,
            "bvps":              info.get("bookValue"),
            "roe":               info.get("returnOnEquity"),
            "marketCap":         market_cap,
            "enterpriseValue":   enterprise_value,
            "evCfo":             ev_cfo,
            "targetPrice":       target_price,
            "peSector":          pe_sector,
        }

        return jsonify(response)

    except Exception as e:
        app.logger.error(f"Error al obtener datos para {ticker}: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
