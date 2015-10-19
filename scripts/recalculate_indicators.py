#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
recalculate_indicators.py

Calculate buffer shape indicators from division indicators. Each buffer will
have an indicator built from a weighted average of divisions intersecting the
buffer.
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import with_statement
import os
import sys
import shapefile

from path_finders import find_shp_path, iter_buffer_dirs
from path_finders import get_indicators_shp_path
from data_loaders import get_indicators, get_weights
import utils
import geo_utils
from geo_utils import calculate_area
from global_vars import IDS_GCBA

POPULATION = "hab"
OMIT_FIELDS = ["Código", "CO_FRACC", "CO_FRAC_RA"]


def _get_indicator_names(df_indicators, omit=OMIT_FIELDS):
    """Return a list with indicator field names."""
    return list(df_indicators.columns.difference(omit))


def _calc_total_poulation(weights, population, skip):
    divisions = weights.keys()

    msg = "\n".join([divisions[0], "not in", repr(population)])
    assert divisions[0] in population, msg

    return sum([(population[division] * weights[division]["division"])
                for division in divisions if division not in skip])


def _calc_indicator(series, weights, population, skip=None):
    """Calculate weighted average indicator."""
    skip = skip or []
    indicator_value = 0.0

    total_population = _calc_total_poulation(weights, population, skip)

    for division in weights.keys():
        if division not in skip:
            division_population = (population[division] *
                                   weights[division]["division"])
            weight = division_population / total_population

            indicator_value += weight * series[division]

    return indicator_value


def _calc_indicators(indicators, df_indicators, weights, area_level,
                     skip=None):
    """Calculate weighted averaged indicators."""
    skip = skip or []

    calculated_indicators = []
    for indicator in indicators:
        if indicator != POPULATION:
            series = df_indicators.set_index(IDS_GCBA[area_level])[indicator]
            pop = df_indicators.set_index(IDS_GCBA[area_level])[POPULATION]
            calculated_indicators.append(
                _calc_indicator(series, weights, pop, skip))
        else:
            calculated_indicators.append(
                _calc_total_poulation(weights, pop, skip))

    return calculated_indicators


def recalculate_indicators(new_shp_dir, area_level, skip=None,
                           subcategory=None, omit_fields=None):
    skip = skip or []
    if omit_fields:
        if not type(omit_fields) == list:
            omit_fields = [omit_fields]
        omit_fields = OMIT_FIELDS
        omit_fields.extend(omit_fields)

    buffer_shp_path = find_shp_path(new_shp_dir)
    shp_name = os.path.basename(buffer_shp_path)

    sf = shapefile.Reader(buffer_shp_path)
    df_indicators = get_indicators(area_level)
    weights = get_weights(buffer_shp_path, area_level)

    w = shapefile.Writer(shapefile.POLYGON)

    indicators = _get_indicator_names(df_indicators)
    for field in sf.fields[1:]:
        w.field(*field)
    for indicator in indicators:
        field = [str(indicator), str("N"), 20, 18]
        w.field(*field)
    w.field(str("area_km2"), str("N"), 20, 18)
    w.field(str("hab_km2"), str("N"), 20, 18)

    for record_shape in sf.iterShapeRecords():
        record = record_shape.record
        shape = record_shape.shape

        # print(record[0])
        if type(record[0]) == int:
            id_record = unicode(record[0])
        else:
            id_record = unicode(record[0].decode("utf-8"))

        if len(weights[id_record]) > 0:
            calculated_indicators = _calc_indicators(indicators,
                                                     df_indicators,
                                                     weights[id_record],
                                                     area_level,
                                                     skip)
            record.extend(calculated_indicators)

            area = calculate_area(shape) / 1000000
            record.append(area)

            population = calculated_indicators[indicators.index(POPULATION)]
            pop_density = population / area
            record.append(pop_density)

            w.record(*record)

            w.poly(shapeType=shapefile.POLYGON, parts=[shape.points])

    path = get_indicators_shp_path(shp_name, subcategory)
    w.save(path)

    utils.copy_prj(buffer_shp_path.decode("utf-8"), path)


def main(buffers_dir=None, skip=None, recalculate=False, area_level="RADIO",
         subcategory=None, omit_fields=None):
    skip = skip or []

    for buffer_dir in iter_buffer_dirs(buffers_dir):
        print("Calculating", os.path.basename(buffer_dir), "indicators")
        sys.stdout.flush()

        buffer_indic_path = get_indicators_shp_path(
            os.path.basename(buffer_dir), "buffers")
        # print(buffer_indic_path + ".shp")
        if not os.path.isfile(buffer_indic_path + ".shp") or recalculate:
            recalculate_indicators(buffer_dir, area_level, skip,
                                   subcategory=subcategory,
                                   omit_fields=omit_fields)

if __name__ == '__main__':
    main()