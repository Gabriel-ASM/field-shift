const MONEY = new Intl.NumberFormat("en-US", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const PERCENT = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 0 });
const COUNT = new Intl.NumberFormat("en-US");

export const money = (value: number) => MONEY.format(value);
export const percent = (value: number) => PERCENT.format(value);
export const count = (value: number) => COUNT.format(value);
