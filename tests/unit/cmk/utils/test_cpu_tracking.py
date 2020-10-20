#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest

import cmk.utils.cpu_tracking as cpu_tracking


def json_identity(serializable):
    return json.loads(json.dumps(serializable))


@pytest.fixture(autouse=True, scope="function")
def reset_cpu_tracking(monkeypatch):
    cpu_tracking.reset()


@pytest.fixture
def set_time(monkeypatch):
    def setter(value):
        monkeypatch.setattr("time.time", lambda value=value: value)

    return setter


class TestCpuTracking:
    @pytest.fixture
    def null(self):
        return cpu_tracking.Snapshot.null()

    @pytest.fixture
    def now(self):
        return cpu_tracking.Snapshot.take()

    def test_eq_neq(self, null, now):
        assert null == cpu_tracking.Snapshot.null()
        assert null != now
        assert now != null

    def test_add_null_null(self, null):
        assert null + null == null

    def test_add_null_now(self, null, now):
        assert null + now == now

    def test_sub_null_null(self, null):
        assert null - null == null

    def test_sub_now_null(self, now, null):
        assert now - null == now

    def test_sub_now_now(self, now, null):
        assert now - now == null

    def test_json_serialization_null(self, null):
        assert cpu_tracking.Snapshot.deserialize(json_identity(null.serialize())) == null

    def test_json_serialization_now(self, now):
        assert cpu_tracking.Snapshot.deserialize(json_identity(now.serialize())) == now


def test_cpu_tracking_initial_times():
    assert cpu_tracking.get_times() == {}


def test_cpu_tracking_initial_state():
    assert not cpu_tracking.is_tracking()


def test_phase_without_tracking():
    assert not cpu_tracking.is_tracking()
    with cpu_tracking.phase("bla"):
        assert not cpu_tracking.is_tracking()
    assert not cpu_tracking.is_tracking()
    assert not cpu_tracking.get_times()


def test_cpu_tracking_simple(set_time):
    set_time(0.0)
    with cpu_tracking.execute("busy"):
        assert cpu_tracking.get_times() == {}
        set_time(1.0)

    times = cpu_tracking.get_times()

    assert len(times) == 2
    assert times["TOTAL"].run_time == 1.0
    assert times["busy"].run_time == 1.0


def test_cpu_tracking_multiple_phases(set_time):
    set_time(0.0)
    with cpu_tracking.execute("busy"):
        set_time(2.0)

        with cpu_tracking.phase("agent"):
            set_time(5.0)

        with cpu_tracking.phase("snmp"):
            set_time(7.0)

    times = cpu_tracking.get_times()
    assert len(times) == 4

    assert times["TOTAL"].run_time == 7.0
    assert times["busy"].run_time == 2.0
    assert times["snmp"].run_time == 2.0
    assert times["agent"].run_time == 3.0


def test_cpu_tracking_add_times(set_time):
    set_time(0.0)
    with cpu_tracking.execute("busy"):
        set_time(2.0)

        with cpu_tracking.phase("agent"):
            set_time(5.0)

        with cpu_tracking.phase("agent"):
            set_time(9.0)

    times = cpu_tracking.get_times()
    assert len(times) == 3

    assert times["TOTAL"].run_time == 9.0, times["TOTAL"]
    assert times["busy"].run_time == 2.0, times["busy"]
    assert times["agent"].run_time == 7.0, times["agent"]


def test_cpu_tracking_nested_times(set_time):
    set_time(0.0)

    with cpu_tracking.execute("one"):
        set_time(2.0)

        with cpu_tracking.phase("two"):
            set_time(4.0)

            with cpu_tracking.phase("three"):
                set_time(6.0)

    times = cpu_tracking.get_times()
    assert len(times) == 4, times.keys()

    assert times["one"].run_time == 2.0
    assert times["two"].run_time == 2.0
    assert times["three"].run_time == 2.0
    assert times["TOTAL"].run_time == 6.0


def test_cpu_tracking_update(set_time):
    set_time(0.0)
    with cpu_tracking.execute("busy"):
        cpu_tracking.update(
            {
                "busy": cpu_tracking.Snapshot(
                    cpu_tracking.times_result([1.0, 2.0, 3.0, 4.0, 5.0]),
                    5.0,
                ),
                "agent": cpu_tracking.Snapshot(
                    cpu_tracking.times_result([1.0, 2.0, 3.0, 4.0, 5.0]),
                    5.0,
                ),
                "test": cpu_tracking.Snapshot(
                    cpu_tracking.times_result([1.0, 2.0, 3.0, 4.0, 5.0]),
                    5.0,
                ),
                "TOTAL": cpu_tracking.Snapshot(
                    cpu_tracking.times_result([3.0, 6.0, 9.0, 12.0, 15.0]),
                    15.0,
                ),
            },)
        with cpu_tracking.phase("agent"):
            set_time(9.0)

    times = cpu_tracking.get_times()
    assert len(times) == 4

    assert times["TOTAL"].run_time == 24.0  # 15 + 9
    assert times["busy"].run_time == 5.0  # 5 + 0
    assert times["agent"].run_time == 14.0  # 5 + 9
    assert times["test"].run_time == 5.0  # 5
