from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import logging

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

@app.route("/datos", methods=["GET"])
def datos():
    ticker = request.args.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Ticker no proporcionado"}), 400

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        # Manejo seguro de cashflow
        try:
            cf_df = stock.cashflow
            if cf_df is None or getattr(cf_df, "empty", False):
                cashflow = {}
            else:
                cashflow = cf_df
        except Exception:
            cashflow = {}

        # Precio con fallback
        precio = info.get("currentPrice") or info.get("regularMarketPrice")

        # FCF directo o calculado
        fcf = info.get("freeCashflow")
        if fcf is None:
            try:
                op = cashflow.get("Total Cash From Operating Activities", [None])[0]
                capex = cashflow.get("Capital Expenditures", [None])[0]
                if op is not None and capex is not None:
                    fcf = op - capex
            except:
                fcf = None

        # EPS y P/E
        eps = info.get("forwardEps") or info.get("epsTrailingTwelveMonths") or 0
        pe  = info.get("forwardPE") or info.get("trailingPE") or None

        # Market cap y enterprise value
        market_cap       = info.get("marketCap")
        enterprise_value = info.get("enterpriseValue")
        ev_cfo           = None
        if fcf and enterprise_value:
            try:
                ev_cfo = round(enterprise_value / fcf, 2)
            except:
                ev_cfo = None

        # Objetivo de precio a 1 año (analyst target mean)
        target_price = info.get("targetMeanPrice")  # suele ser el consensus one-year target

        response = {
            "ticker":         ticker,
            "precio":         precio,
            "fcf":            fcf,
            "wacc":           0.08,
            "g":              0.02,
            "acciones":       info.get("sharesOutstanding"),
            "dividendo":      info.get("dividendRate"),
            "eps":            eps,
            "pe":             pe,
            "bvps":           info.get("bookValue"),
            "roe":            info.get("returnOnEquity"),
            "marketCap":      market_cap,
            "enterpriseValue": enterprise_value,
            "evCfo":          ev_cfo,
            "targetPrice":    target_price
            # NUEVOS -----------------
            "sharesOutstanding": shares_outstanding,
            "cash":              cash,
            "debt":              debt,
        }

        return jsonify(response)

    except Exception as e:
        app.logger.error(f"Error al obtener datos para {ticker}: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
