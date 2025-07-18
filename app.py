from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import logging

app = Flask(__name__)
CORS(app)

# Configura logging a stdout para que Render lo capture
logging.basicConfig(level=logging.INFO)

@app.route("/datos", methods=["GET"])
def datos():
    ticker = request.args.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Ticker no proporcionado"}), 400

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        cashflow = stock.cashflow or {}

        # Calcular FCF
        fcf = None
        try:
            op = cashflow.get("Total Cash From Operating Activities", [None])[0]
            capex = cashflow.get("Capital Expenditures", [None])[0]
            if op is not None and capex is not None:
                fcf = op - capex
        except Exception:
            fcf = None

        # Otros campos financieros
        market_cap = info.get("marketCap")
        enterprise_value = info.get("enterpriseValue")

        ev_cfo = None
        if fcf:
            try:
                ev_cfo = round(enterprise_value / fcf, 2) if enterprise_value else None
            except Exception:
                ev_cfo = None

        response = {
            "ticker": ticker,
            "precio":      info.get("currentPrice"),
            "fcf":         fcf,
            "wacc":        0.08,
            "g":           0.02,
            "acciones":    info.get("sharesOutstanding"),
            "dividendo":   info.get("dividendRate"),
            "eps":         info.get("forwardEps") or info.get("epsTrailingTwelveMonths"),
            "pe":          info.get("trailingPE"),
            "bvps":        info.get("bookValue"),
            "roe":         info.get("returnOnEquity"),
            "marketCap":   market_cap,
            "enterpriseValue": enterprise_value,
            "evCfo":       ev_cfo
        }

        return jsonify(response)

    except Exception as e:
        app.logger.error(f"Error al obtener datos para {ticker}: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
