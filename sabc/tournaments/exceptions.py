"""Exceptions for Tournaments and Results"""


class TournamentNotComplete(Exception):
    """Exception for trying to do Result operations for a tournament still in progress"""
