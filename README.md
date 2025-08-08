# MDB93 Scalping Bot (Demo/Reale) – Ready for Render

Web dashboard mobile-first con:
- Grafico **a candele** + **EMA 9/21**
- **Multi-crypto** (BTC/USDT, ETH/USDT, SOL/USDT)
- **Profitto giornaliero** e storico per coppia
- **Filtro EMA** che limita ingressi contro-trend (conteggio trade evitati)
- **Switch Demo/Reale** dalla UI
- Stake, TP/SL modificabili da dashboard
- Nessuna chiusura forzata quando cambi coppia (chiude solo a TP/SL)

## Deploy rapido su Render
1. Crea un nuovo **Web Service** su https://render.com collegando questo progetto (o carica lo zip su un repo Git).
2. Imposta **Start Command**: `python app.py`
3. Porta: `8000`
4. **Environment variables** (sicurezza – mai in chiaro nel codice):
   - `TESTNET_API_KEY` = *la tua API di testnet*
   - `TESTNET_API_SECRET` = *la tua SECRET di testnet*
   - (opzionale per reale) `REAL_API_KEY`, `REAL_API_SECRET`
   - `DEFAULT_MODE` = `DEMO`
   - `STAKE` = `500`
5. Deploy → apri l’URL pubblico → Login: **MDB93** / **scalping2025**

> Nota: il grafico usa dati pubblici Binance (endpoint pubblico) anche in modalità Demo. I trade Demo usano le API Testnet.

## Avvertenze sicurezza
- In modalità **REALE**, abilita solo **Spot & Margin trading** nelle chiavi. **NON** abilitare `Withdraw`.
- Gestisci le chiavi tramite **environment variables**, mai nel codice.

## Personalizzazione
- Aggiungi simboli nel file `bot.py` → `self.allowed_symbols`
- Cambia timeframe grafico editando `static/app.js` (endpoint klines).

Buon trading! (in demo prima 😉)
