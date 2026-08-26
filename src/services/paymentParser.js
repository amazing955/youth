const amountPattern = /(?:UGX|USh|=)\s?([\d,]+(?:\.\d{2})?)/i
const transactionPattern = /(?:transaction|txn|id|reference)\s*(?:id|no|number|:)?\s*([A-Z0-9-]{6,})/i
const phonePattern = /(\+?256\s?\d{3}\s?\d{6})/

function parseCommonMessage(message) {
  const amountMatch = message.match(amountPattern)
  const transactionMatch = message.match(transactionPattern)
  const phoneMatch = message.match(phonePattern)
  return {
    amount: amountMatch ? Number(amountMatch[1].replace(/,/g, '')) : null,
    transaction_id: transactionMatch ? transactionMatch[1] : null,
    phone_number: phoneMatch ? phoneMatch[1].replace(/\s/g, '') : null,
  }
}

export function parseMtnMessage(message, receivedAt = new Date().toISOString()) {
  if (!/mtn|mobile money|momo/i.test(message)) return null
  return { provider: 'MTN', payment_time: receivedAt, ...parseCommonMessage(message) }
}

export function parseAirtelMessage(message, receivedAt = new Date().toISOString()) {
  if (!/airtel money|airtel/i.test(message)) return null
  return { provider: 'Airtel', payment_time: receivedAt, ...parseCommonMessage(message) }
}

export function parsePaymentMessage(message, receivedAt) {
  return parseMtnMessage(message, receivedAt) || parseAirtelMessage(message, receivedAt)
}
