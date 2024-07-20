# -*- coding: utf-8 -*-
import calendar
import datetime


def get_last_sunday(month=0):
    month = month or datetime.date.today().month
    return max(
        week[-1] for week in calendar.monthcalendar(datetime.date.today().year, month)
    )


# TPW Length-weight Conversion Table for Texas Largemouth Bass
# https://tpwd.texas.gov/fishboat/fish/recreational/catchrelease/bass_length_weight.phtml
#
# Inches	Fractions
#  	       0	 1/8	 1/4	 3/8	 1/2	 5/8	 3/4	 7/8
# 10	0.48	0.50	0.52	0.54	0.56	0.58	0.61	0.63
# 11	0.66	0.68	0.71	0.73	0.76	0.79	0.81	0.84
# 12	0.87	0.90	0.93	0.97	1.00	1.03	1.07	1.10
# 13	1.14	1.17	1.21	1.25	1.29	1.32	1.37	1.41
# 14	1.45	1.49	1.54	1.58	1.63	1.67	1.72	1.77
# 15	1.82	1.87	1.92	1.97	2.02	2.08	2.13	2.19
# 16	2.25	2.31	2.36	2.42	2.49	2.55	2.61	2.68
# 17	2.74	2.81	2.88	2.95	3.02	3.09	3.16	3.23
# 18	3.31	3.39	3.46	3.54	3.62	3.70	3.78	3.87
# 19	3.95	4.04	4.13	4.22	4.31	4.40	4.49	4.58
# 20	4.68	4.78	4.87	4.97	5.08	5.18	5.28	5.39
# 21	5.49	5.60	5.71	5.82	5.94	6.05	6.17	6.28
# 22	6.40	6.52	6.64	6.77	6.89	7.02	7.15	7.28
# 23	7.41	7.54	7.68	7.81	7.95	8.09	8.23	8.38
# 24	8.52	8.67	8.82	8.97	9.12	9.27	9.43	9.59
# 25	9.75	9.91	10.07	10.23	10.40	10.57	10.74	10.91
# 26	11.09	11.26	11.44	11.62	11.80	11.99	12.17	12.36
# 27	12.55	12.74	12.94	13.13	13.33	13.53	13.73	13.94
# 28	14.15	14.35	14.56	14.78	14.99	15.21	15.43	15.65
# 29	15.87	16.10	16.33	16.56	16.79	17.03	17.26	17.50
LENGTH_TO_WEIGHT = {
    #     0    1/8    1/4   3/8   1/2   5/8   3/4   7/8
    # 10: [0.48, 0.50, 0.52, 0.54, 0.56, 0.58, 0.61, 0.63],
    # 11: [0.66, 0.68, 0.71, 0.73, 0.76, 0.79, 0.81, 0.84],
    12: [0.87, 0.90, 0.93, 0.97, 1.00, 1.03, 1.07, 1.10],
    13: [1.14, 1.17, 1.21, 1.25, 1.29, 1.32, 1.37, 1.41],
    14: [1.45, 1.49, 1.54, 1.58, 1.63, 1.67, 1.72, 1.77],
    15: [1.82, 1.87, 1.92, 1.97, 2.02, 2.08, 2.13, 2.19],
    16: [2.25, 2.31, 2.36, 2.42, 2.49, 2.55, 2.61, 2.68],
    17: [2.74, 2.81, 2.88, 2.95, 3.02, 3.09, 3.16, 3.23],
    18: [3.31, 3.39, 3.46, 3.54, 3.62, 3.70, 3.78, 3.87],
    19: [3.95, 4.04, 4.13, 4.22, 4.31, 4.40, 4.49, 4.58],
    20: [4.68, 4.78, 4.87, 4.97, 5.08, 5.18, 5.28, 5.39],
    21: [5.49, 5.60, 5.71, 5.82, 5.94, 6.05, 6.17, 6.28],
    22: [6.40, 6.52, 6.64, 6.77, 6.89, 7.02, 7.15, 7.28],
    23: [7.41, 7.54, 7.68, 7.81, 7.95, 8.09, 8.23, 8.38],
    24: [8.52, 8.67, 8.82, 8.97, 9.12, 9.27, 9.43, 9.59],
    25: [9.75, 9.91, 10.07, 10.23, 10.40, 10.57, 10.74, 10.91],
    26: [11.09, 11.26, 11.44, 11.62, 11.80, 11.99, 12.17, 12.36],
    27: [12.55, 12.74, 12.94, 13.13, 13.33, 13.53, 13.73, 13.94],
    28: [14.15, 14.35, 14.56, 14.78, 14.99, 15.21, 15.43, 15.65],
    29: [15.87, 16.10, 16.33, 16.56, 16.79, 17.03, 17.26, 17.50],
}


def get_weight_from_length(length):
    """Returns the weight of a fish, given its length

    if the length is below 10 inches: 0.00 (lbs) is returned
    if the length is greater than 29 inches: 18.00 (lbs) is returned

    Fractional inch measurements for reference:
      0 = 0.00
    1/8 = 0.125
    1/4 = 0.25
    3/8 = 0.375
    1/2 = 0.50
    5/8 = 0.625
    3/4 = 0.75
    7/8 = 0.875
    """
    inches = int(str(length).split(".", maxsplit=1)[0])
    fraction = float(f"0.{str(length).split('.')[1]}")
    if inches > 29:
        return 18.00

    fractions = {
        0.00: 0,
        0.125: 1,
        0.25: 2,
        0.375: 3,
        0.50: 4,
        0.625: 5,
        0.75: 6,
        0.875: 7,
    }
    if inches in LENGTH_TO_WEIGHT:
        return LENGTH_TO_WEIGHT[inches][fractions[fraction]]

    return 0.00


def get_length_from_weight(weight):
    """Given a fishes weight, return its length

    if the weight is less than 0.48 pounds: 10.00 (inches) is returned
    if the weight is greater than 17.50 pounds: 30.00 (inches) is returned

    Fractional inch measurements for reference:
    0: 0.00   0
    1: 0.125 1/8
    2: 0.25  1/4
    3: 0.375 3/8
    4: 0.50  1/2
    5: 0.625 5/8
    6: 0.75  3/4
    7: 0.875 7/8
    """
    if weight > 17.50:
        return 30.0

    fractions = {
        0: 0.00,
        1: 0.125,
        2: 0.25,
        3: 0.375,
        4: 0.50,
        5: 0.625,
        6: 0.75,
        7: 0.875,
    }
    index = 0
    inches = 0
    for inch, weights in LENGTH_TO_WEIGHT.items():
        # Find inch range for the weight
        if all([weight >= min(weights), weight <= max(weights)]):
            inches = inch
            # Get the closest fractional weight
            closest: float = min(weights, key=lambda w: abs(w - weight))
            index = weights.index(closest)
            break

    return inches + fractions[index]
