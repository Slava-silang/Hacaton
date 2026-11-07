#!/usr/bin/env python3
"""Reproduce Gemini inputs, not validate or forecast demand.

Run: python3 research/audit_calculations.py [--routes]
All money inputs are RUB, all decimals are exact; print final monetary results
in RUB millions with ROUND_HALF_UP. Route rows retain the supplied order (1–12).
No package installation, network, or input files are required.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import sys

D = Decimal
WEEKS, SEATS = D(52), D(100)
P0, M0 = D(2700000), D(108900000)  # case references, not a 2027 forecast
MILLION = D(1000000)


def decimals(values):
    return tuple(D(str(x)) for x in values)


@dataclass(frozen=True)
class Scenario:
    name: str
    frequencies: tuple
    one_way_hours: tuple
    load_factor: Decimal
    blended_revenue_per_passenger: tuple  # includes unidentified subsidy
    cost_per_block_hour: Decimal
    fixed_cost: Decimal
    ferry_factor: Decimal

    def calculate(self):
        seats = tuple(2 * WEEKS * SEATS * f for f in self.frequencies)
        passengers = tuple(k * self.load_factor for k in seats)
        revenue = sum(q * y for q, y in zip(passengers, self.blended_revenue_per_passenger))
        hours = sum(2 * f * h for f, h in zip(self.frequencies, self.one_way_hours))
        total_hours = hours * (1 + self.ferry_factor)
        cost = total_hours * WEEKS * self.cost_per_block_hour + self.fixed_cost
        return {
            "seats": sum(seats), "passengers": sum(passengers), "rows": passengers,
            "hours": hours, "total_hours": total_hours, "revenue": revenue,
            "cost": cost, "result": revenue - cost,
            "break_even_lf": self.load_factor * cost / revenue,
            "blended_yield": revenue / sum(passengers),
        }


F1 = ((7, 7, 5, 5, 5, 3, 4, 3, 3, 2, 4, 3), (5, 5, 4, 4, 3, 2, 3, 2, 2, 2, 3, 2))
F2 = ((4, 5, 6, 3, 4, 5, 4, 5, 5, 5, 4, 5), (3, 4, 4, 2, 3, 4, 3, 4, 4, 4, 3, 4))
T1 = decimals((2.4, 2.5, 2, 2.9, 2.3, 2.4, 2.2, 3.3, 3.6, 4.2, 2.4, 2.3))
T2 = decimals((2.3, 1.5, 1.2, 3.1, 2.9, 2.8, 2.3, 2.9, 2.2, 1.6, 2.9, 3))
Y1 = (decimals((9024, 9870, 8648, 12596, 10152, 10340, 8554, 10904, 12690, 13912, 15792, 11186)),
      decimals((8256, 9030, 7912, 11524, 9288, 9460, 7826, 9976, 11610, 12728, 14448, 10234)))
Y2 = decimals((10400, 8100, 7400, 12600, 12200, 13900, 11600, 13900, 9600, 8800, 11900, 12400))
SCENARIOS = (
    Scenario("H1 base", F1[0], T1, D('.80'), Y1[0], D(318000), D(180000000), D(0)),
    Scenario("H1 cautious", F1[1], T1, D('.72'), Y1[1], D(318000), D(180000000), D(0)),
    Scenario("H2 base", F2[0], T2, D('.86'), Y2, D(330000), D(25000000), D('.035')),
    Scenario("H2 cautious", F2[1], T2, D('.79'), tuple(y * D('.91') for y in Y2), D(330000), D(25000000), D('.055')),
)


def fmt(value, places=2):
    quantum = D(1).scaleb(-places)
    return str(D(value).quantize(quantum, rounding=ROUND_HALF_UP))


def main():
    print("CONDITIONAL REPRODUCTION: supplied capacity, load factors, revenue and cost assumptions; NOT demand forecasts.")
    print("name | pairs/week | seats/year | pax/year | commercial h/week | total h/week | revenue RUBm | cost RUBm | result RUBm | BE load %")
    for scenario in SCENARIOS:
        x = scenario.calculate()
        print(" | ".join((scenario.name, str(sum(scenario.frequencies)), fmt(x['seats'], 0), fmt(x['passengers'], 0),
                          fmt(x['hours'], 1), fmt(x['total_hours'], 3), fmt(x['revenue'] / MILLION),
                          fmt(x['cost'] / MILLION), fmt(x['result'] / MILLION), fmt(100 * x['break_even_lf']))))
        print(f"  Fixed-denominator gross share: {fmt((P0 + x['passengers']) / M0 * 100, 4)}%; increase {fmt(x['passengers'] / M0 * 100, 4)} pp (not net growth).")
        print(f"  Gross share if every unit is new market traffic: {fmt((P0 + x['passengers']) / (M0 + x['passengers']) * 100, 4)}%.")
        print(f"  Blended revenue/pax {fmt(x['blended_yield'])}; cost/revenue {fmt(100 * x['cost'] / x['revenue'])}%; result/pax {fmt(x['result'] / x['passengers'])} RUB.")
        if '--routes' in sys.argv:
            for i, (f, h, y, q) in enumerate(zip(scenario.frequencies, scenario.one_way_hours, scenario.blended_revenue_per_passenger, x['rows']), 1):
                print(f"    row {i:02}: pairs={f}; hours/leg={h}; blended_revenue/pax={y}; pax={fmt(q, 0)}; revenue RUBm={fmt(q * y / MILLION)}")

    print("\nSensitivity: fixed base-case frequencies/cost; LF common to all routes; blended revenue scales with LF.")
    print("LF % | H1 result RUBm | H2 result RUBm | H2 result at -10% blended yield RUBm")
    b1, b2 = SCENARIOS[0].calculate(), SCENARIOS[2].calculate()
    for lf in decimals(('.70', '.75', '.80', '.85', '.90')):
        e1 = b1['revenue'] * lf / D('.80') - b1['cost']
        e2 = b2['revenue'] * lf / D('.86') - b2['cost']
        e2_low = b2['revenue'] * lf / D('.86') * D('.90') - b2['cost']
        print(f"{fmt(lf * 100, 0)} | {fmt(e1 / MILLION)} | {fmt(e2 / MILLION)} | {fmt(e2_low / MILLION)}")

    print("\nILLUSTRATION ONLY: unidentified baseline of 12/24/36 pairs per week across the same network, LF85%, full year; zero cannibalization assumed.")
    print("equivalent pairs/row/week | baseline pax | H2 net pax | conditional net share % | increase pp")
    for f0 in (1, 2, 3):
        baseline = 12 * f0 * 2 * WEEKS * SEATS * D('.85')
        net = b2['passengers'] - baseline
        print(f"{f0} | {fmt(baseline, 0)} | {fmt(net, 0)} | {fmt((P0 + net) / M0 * 100, 4)} | {fmt(net / M0 * 100, 4)}")

    print("\nOther arithmetic checks:")
    weights = decimals(('.15', '.15', '.20', '.20', '.15', '.15'))
    scores = {'Samara': (9.5, 7.5, 9, 9, 7.5, 8.5), 'Kazan': (8, 9, 8.5, 6.5, 9.5, 9.5), 'Ufa': (7.5, 8.5, 8, 8.5, 8.5, 9)}
    for name, values in scores.items():
        score = sum(w * v for w, v in zip(weights, decimals(values)))
        print(f"  {name}: exact {score}; half-up {fmt(score)}; half-even {score.quantize(D('.01'))}")
    print(f"  H2/H1 base passenger ratio: {fmt(D(55) / D(51) * D('.86') / D('.80'), 6)}")
    print(f"  Rotation totals: pairs={sum((10, 12, 9, 10, 11, 3))}, hours={sum(decimals((46.4, 43.2, 48.2, 52.8, 58.2, 16.4)))}, passengers={sum((89440, 107328, 80496, 89440, 98384, 26832))}")
    print(f"  H2 base, 5 active aircraft: {fmt(b2['total_hours'] / 5 / 7, 3)} block h/day/active aircraft; not a schedule proof.")
    cautious = SCENARIOS[3].calculate()
    print(f"  H2 cautious, 4 active aircraft: {fmt(cautious['total_hours'] / 4 / 7, 3)}; 3 active+1 spare: {fmt(cautious['total_hours'] / 3 / 7, 3)} block h/day/active aircraft.")
    print(f"  25,000 seats/month * 12 * 85% = {fmt(D(25000) * 12 * D('.85'), 0)} pax; 223,000 implies {fmt(D(223000) / (D(25000) * D('.85')), 4)} months.")
    print(f"  Cost rate reduction (330-318)/330 = {fmt((D(330) - 318) / 330 * 100, 4)}%; 8% discount on entire 330 gives {fmt(D(330) * D('.92'))} thousand RUB/h.")
    print(f"  H2 base gross volume over 26 weeks = {fmt(b2['passengers'] / 2, 0)} (only an upper-calendar illustration for H2-year start).")


if __name__ == '__main__':
    main()
