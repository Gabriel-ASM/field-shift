const MONEY = new Intl.NumberFormat("en-US", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const PERCENT = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 0 });
const COUNT = new Intl.NumberFormat("en-US");

export const money = (value: number) => MONEY.format(value);
const SMALL_PERCENT = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });

/** Whole percents, with one decimal below 10% so small shares do not all read "0%". */
export const percent = (value: number) => (value < 0.1 ? SMALL_PERCENT : PERCENT).format(value);
export const count = (value: number) => COUNT.format(value);
