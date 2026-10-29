"""Imported first by every test module that builds the display's data.

Points the settings at config.example.yaml and the MBTA lookup tables (which platform belongs to which station, each route's stops) at
tests/fixtures/lookup, a snapshot taken in October 2026, so the tests run offline and give the same
answers whatever is in cache/. The snapshot includes terminal platforms such as Alewife-01, which the
sample data uses and which the API's own listing does not always return.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["MBTA_CACHE_DIR"] = os.path.join(HERE, "fixtures", "lookup")
# The example settings, not whoever's config.yaml is in the folder: the results must be the same for everyone.
os.environ["MBTA_CONFIG"] = os.path.join(os.path.dirname(HERE), "config.example.yaml")
