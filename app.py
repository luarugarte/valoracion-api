from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)  # Permite acceso desde Lovable (evita errores CORS)

@app.route("/datos", methods=["GET"])
def datos():
    ticker = request.args.get("ticker", "AAPL")
    stock = yf.Ticker(ticker)
    info = stock.info

    return jsonify({
        "ticker": ticker.upper(),
        "precio": info.get("currentPrice"),
        "fcf": info.get("freeCashflow"),
        "marketCap": info.get("marketCap"),
        "enterpriseValue": enterprise_value,
        # Calcula evCfo solo si tienes ambos valores
        "evCfo": (enterprise_value and fcf) and round(enterprise_value / fcf, 2),
        "acciones": info.get("sharesOutstanding"),
        "wacc": 0.08,  # Valor por defecto
        "g": 0.02,     # Valor por defecto
        "dividendo": info.get("dividendRate"),
        "roe": info.get("returnOnEquity"),
        "bvps": info.get("bookValue"),
        "eps": info.get("forwardEps"),
        "pe": info.get("trailingPE"),
        "evToEbitda": info.get("enterpriseToEbitda"),
        "ebitda": info.get("ebitda")
    })
