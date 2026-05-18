"""Tests for forskrifter integration."""
from lovdata_publisher.formatter import refid_to_filepath


def test_refid_to_filepath_routes_lov():
    assert refid_to_filepath("lov/1998-07-17-56") == "lover/lov-1998-07-17-56.md"


def test_refid_to_filepath_routes_forskrift():
    assert refid_to_filepath("forskrift/2024-06-21-1166") == "forskrifter/forskrift-2024-06-21-1166.md"


def test_refid_to_filepath_lov_with_multiple_slashes():
    # The current implementation replaces all slashes — ensure that's stable
    assert refid_to_filepath("lov/2025-06-20-106") == "lover/lov-2025-06-20-106.md"
