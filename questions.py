# """
# Legacy questionnaire template question engine (DEPRECATED).

# This project now uses flows.py (tree-structured engine).
# Do not add SQLAlchemy models here.

# If something still imports questions.py, it should not crash the app.
# """

# from enum import Enum

# # Keep enum only if any old code still references it.
# class QuestionType(str, Enum):
#     YES_NO = "YES_NO"
#     NUMBER = "NUMBER"
#     TEXT = "TEXT"
#     SINGLE_CHOICE = "SINGLE_CHOICE"
#     MULTI_CHOICE = "MULTI_CHOICE"
#     SCALE = "SCALE"
