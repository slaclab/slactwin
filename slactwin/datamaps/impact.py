from lcls_live.datamaps import get_datamaps, TabularDataMap
import pandas
import re

# TODO(pjm): this should be part of lcls-live


def as_impact(tabular, pvdata):
    """
    Return a dict of (name, value) pairs to be read by lume-impact.
    """

    def _process(element, attribute, value, factor, offset, valid_val):
        if not valid_val:
            return ()
        if factor != 1:
            value *= factor
        if offset != 0:
            value += offset
        return impact_field_name(element, attribute), value

    result = tabular.evaluate(pvdata)
    return dict(filter(None, [_process(*v) for v in zip(*result)]))


def get_impact_datamaps(model: str):
    """
    Processes the Bmad datamaps for use with an Impact-T simulation.

    Converts the attribute name, scaling factor, and units to match Impact-T.

    Args:
        model (str): Beamline name (currently cu_inj or sc_inj)
    Returns:
        dict of name:datamap
    """

    _CHARGE_PV = dict(
        # cu_spec provides PVs for cu_inj
        cu_spec="BPMS:IN20:221:TMIT1H",
        sc_inj="BPMS:GUNB:314:TMIT",
    )

    def _bpms(dataframe):
        # only interested in the initial charge BPM
        charge_pvname = _CHARGE_PV[model]
        r = dataframe[res["bpms"].data["pvname"] == charge_pvname]
        return pandas.DataFrame(
            dict(
                impact_name=[""],
                pvname=[charge_pvname],
                impact_factor=r["impact_factor"],
                impact_attribute=["total_charge"],
                impact_unit=r["impact_unit"],
            )
        )

    def _cavities(dataframe):
        _set_column_value(dataframe, "impact_attribute", "phi0", "autophase_deg")
        _set_column_value(
            dataframe, "impact_attribute", "field_autoscale", "rf_field_scale"
        )
        _set_column_value(dataframe, "impact_unit", "2pi", 1, field="impact_factor")
        _set_column_value(dataframe, "impact_unit", "2pi", "deg")
        return dataframe

    def _linac(dataframe):
        df = dataframe[["impact_name", "pvname", "impact_factor", "impact_attribute"]]
        df["impact_unit"] = None
        df.loc[df["impact_attribute"] == "phi0", "impact_name"] += "_phase"
        df.loc[df["impact_attribute"] == "voltage", "impact_name"] += "_scale"
        _set_column_value(df, "impact_attribute", "phi0", 1, field="impact_factor")
        _set_column_value(df, "impact_attribute", "phi0", "deg", field="impact_unit")
        _set_column_value(df, "impact_attribute", "phi0", "dtheta0_deg")
        _set_column_value(df, "impact_attribute", "voltage", "V", field="impact_unit")
        return df

    def _quad(dataframe):
        return dataframe

    def _quad_corrector(dataframe):
        # 0 length corrector quads is mapped to 0.21 m, see cu_inj Impact-T.in
        _DEFAULT_QUAD_CORRECTOR_LENGTH = 0.21
        _set_column_value(
            dataframe, "impact_attribute", "k1l", "T/m", field="impact_unit"
        )
        _set_column_value(
            dataframe,
            "impact_attribute",
            "k1l",
            -1 / _DEFAULT_QUAD_CORRECTOR_LENGTH / 10,
            field="impact_factor",
        )
        _set_column_value(dataframe, "impact_attribute", "k1l", "b1_gradient")
        return dataframe

    def _solenoid(dataframe):
        _set_column_value(
            dataframe, "impact_attribute", "bs_field", "solenoid_field_scale"
        )
        return dataframe

    if model == "cu_inj":
        # cu_inj isn't defined in lcls-live
        # the cu_spec model contains the PVs needed for the cu_inj Impact-T sim
        model = "cu_spec"
    res = {}
    map_functions = dict(
        bpms=_bpms,
        cavities=_cavities,
        linac=_linac,
        quad=_quad,
        quad_corrector=_quad_corrector,
        solenoid=_solenoid,
    )
    for name, dm in get_datamaps(model).items():
        # could call functions from locals() directly to call methods,
        # but map_functions is more explicit
        if name in map_functions:
            res[name] = _update_datamap_for_code(dm, "impact")
            res[name].data = map_functions[name](res[name].data)
    return res


def impact_field_name(element, attribute):
    """Returns the full element field name, which can be used set set lume-impact values"""
    return ":".join([v for v in (element, attribute) if v])


def _update_datamap_for_code(tabular, accelerator_code: str):
    """
    Create a new TabularDataMap with code-specific name.

    This function replaces any leading occurrences of 'bmad' or 'tao'
    in datamap fields with the provided accelerator_code.

    Returns:
        TabularDataMap a new TabularDataMap instance with updated naming
    """

    def _rename_value(value):
        return re.sub(r"^(bmad|tao)", accelerator_code, value)

    def _rename_columns(dataframe):
        return dataframe.rename(
            columns=dict([(n, _rename_value(n)) for n in dataframe.columns])
        )

    return TabularDataMap(
        data=_rename_columns(tabular.data),
        pvname=tabular.pvname,
        element="impact_name",
        attribute="impact_attribute",
        factor="impact_factor",
        use_des=tabular.use_des,
    )


def _set_column_value(dataframe, match_column: str, match_value, new_value, field=None):
    dataframe.loc[dataframe[match_column] == match_value, field or match_column] = (
        new_value
    )
