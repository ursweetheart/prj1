/* Same rule as backend pipeline/knowledge.needs_price_approval, to pick the right button before saving
 * (the server decides): kind 'price', or a number followed by a money unit that ends there. */
const MONEY = /\d[\d.,]*\s*(?:(?:triệu|tr|tỷ|ty|nghìn|ngàn|k|đồng|đ|vnđ|vnd|usd)(?![\p{L}\p{N}_])|\$)|\/\s*m(?:2|²)/iu

export const needsPriceApproval = (kind, content) => kind === 'price' || MONEY.test(content || '')
