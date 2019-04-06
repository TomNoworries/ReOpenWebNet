#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from openwebnet import CommandClient

__author__ = "Pippocla"
__copyright__ = "Pippocla"
__license__ = "mit"


def test_CommandClient():
    client = CommandClient('192.168.1.10', 20000, '123456')
    assert client._host == '192.168.1.10'
    assert client._port == 20000
    assert client._password == '123456'
