# Android SMS integration boundary

The browser build never reads SMS. The React UI is Capacitor-ready and opens provider USSD using a `tel:` URI. The Android implementation should be added as a native Capacitor plugin with these responsibilities:

1. Request `READ_SMS`/notification access only after a member enables payment reconciliation, with clear consent.
2. Receive only matching MTN/Airtel notification events; do not scan or upload the inbox.
3. Parse provider messages with `src/services/paymentParser.js` (or an equivalent Kotlin parser) and send only provider, transaction ID, amount, payment time, and SACCO number to `POST /api/payments/reconcile/` using the stored auth token.
4. Use Android's intent/dialer flow for `tel:` USSD URIs. Automatic USSD execution is device/provider-dependent and must not bypass Android security controls.

Typical packaging commands:

```bash
npm run build
npx cap add android
npx cap sync android
npx cap open android
```

A native SMS plugin is intentionally not fabricated in the browser project: SMS access requires Android permissions and a reviewed native implementation.
