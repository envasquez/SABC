"""Exceptions for Tournaments and Results"""


class TournamentNotComplete(Exception):
    """Exception for trying to do Result operations for a tournament still in progress"""


class IncorrectTournamentType(Exception):
    """Exception for trying to do team operations on a non-team tournament"""
