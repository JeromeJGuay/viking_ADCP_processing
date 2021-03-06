"""
Author : jerome.guay@protonmail.com
Date : 29-04-2021

Module to open and write  ODF (Ocean Data Format) files used by Maurice Lamontagne Institute.

ODF class method:
----------
read()

save()

to_dataset()

add_buoy_instrument()

add_general_cal()

add_polynomial_cal()

add_compass_cal()

add_history()

add_parameter()

from_dataframe()

Notes
-----
ODF object structure:
    Headers are stored as dictionnaries containing. They are either direction attributes or store
    in one of the following attributes .buoy_instrument, .general_cal, .polynomial_cal, .compass, .history
    or .parameter.
    Data are pandas dataframe. ODF.data.
Writing ODF files.
    Using .save(filename), the ODF file will be written.
    - Headers keys are always printed in upper case.
    Headers values can be one of: int, float, str, list, tuple, or list(tuple).
      - floats are printed with the number of significan digit specified by the gloabal variable PRECISION.
      - list elements are printed with the same headers key.
      - coefficients, directions and corrections items need to be stored as tuple for the correct formatting
        field width of 12 and 8 decimals precision.
"""


import typing as tp
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

NA_REP = "null"  # There should not be any null value in a odf file.
SPACE = " "  # single space
INDENT = "  "  # double space
NEWLINE = "\n"  # new line
PRECISION = 6

REPEATED_HEADERS = [
    "buoy_instrument",
    "general_cal",
    "polynomial_cal",
    "compass_cal",
    "history",
    "parameter",
]

HEADERS_DEFAULT = dict(
    odf=dict(file_specification=""),
    cruise=dict(
        country_institute_code="",
        cruise_number="",
        organization="",
        chief_scientist="",
        start_date="",
        end_date="",
        platform="",
        cruise_name="",
        cruise_description="",
    ),
    event=dict(
        data_type="",
        event_number="",
        event_qualifier1="",
        event_qualifier2="",
        creation_date="",
        orig_creation_date="",
        start_date_time="",
        end_date_time="",
        initial_latitude=None,
        initial_longitude=None,
        end_latitude=None,
        end_longitude=None,
        min_depth=None,
        max_depth=None,
        sampling_interval=None,
        sounding=None,
        depth_off_bottom=None,
        event_comments=[],
    ),
    buoy=dict(
        name="",
        type="",
        model="",
        height="",
        diameter="",
        weight="",
        description="",
    ),
    plankton=dict(
        water_volume="",
        volume_method="",
        lrg_plankton_removed="",
        collection_method="",
        mesh_size="",
        phase_of_daylight="",
        collector_dplmt_id="",
        collector_sample_id="",
        procedure="",
        preservation="",
        storage="",
        meters_sqd_flag="",
        plankton_comments=[],
    ),
    meteo=dict(
        air_temperature=None,
        atmospheric_pressure=None,
        wind_speed=None,
        wind_direction=None,
        sea_state=None,
        cloud_cover=None,
        ice_thickness=None,
        meteo_comments=[],
    ),
    instrument=dict(
        inst_type="",
        model="",
        serial_number="",
        description="",
    ),
    quality=dict(
        quality_date="",
        quality_tests=[],
        quality_comments=[],
    ),
    record=dict(
        num_calibration=None,
        num_swing=None,
        num_history=None,
        num_cycle=None,
        num_param=None,
    ),
)

REPEATED_HEADERS_DEFAULT = dict(
    buoy_instrument=dict(
        name="",
        type="",
        model="",
        serial_number="",
        description="",
        inst_start_date_time="",
        inst_end_date_time="",
        buoy_instrument_comments=[],
        sensors=[],
    ),
    general_cal=(
        dict(
            parameter_code="",
            calibration_type="",
            calibration_date="",
            application_date="",
            number_coefficients=0,
            coefficients=(),  # NOTE for i in number_coefficients ' %12.8e '
            calibration_equation=[],
            calibration_comments=[],
        ),
    ),
    polynomial_cal=dict(
        parameter_code="",
        calibration_date="",
        application_date="",
        number_coefficients=0,
        coefficients=(),  # NOTE for i in number_coefficients ' %12.8e '
    ),
    compass_cal=dict(
        parameter_code="",
        calibration_date="",
        application_date="",
        # NOTE for j = 0:8 % 12.8e   % 12.8e   % 12.8e   % 12.8e, [(4*j) +1:(4*j)+4] # 8 FW.DP
        directions=(),
        corrections=(),
    ),
    history=dict(creation_date="", process=[]),
    parameter=dict(
        type="",
        name="",
        units="",
        code="",
        null_value=0,
        print_field_width=10,
        print_decimal_places=4,
        angle_of_section=0,
        magnetic_variation=0,
        depth=0,
        minimum_value=0,
        maximum_value=0,
        number_valid=0,
        number_null=0,
    ),
)


class Odf:
    """
    ODF class object can make, read and write ODF (ocean data format) files.

    Usefull methods
    ---------------
    read()

    save()

    to_dataset()

    add_instruments()

    add_parameter()

    from_dataframe()

    Notes
    -----
    ODF object structure:
        Headers are stored as dictionnaries containing. They are either direction attributes or store
        in one of the following attributes .buoy_instrument, .general_cal, .polynomial_cal, .compass, .history
        or .parameter.
    Data are pandas dataframe. ODF.data.
        Writing ODF files.
        Using .save(filename), the ODF file will be written.
        - Headers keys are always printed in upper case.
        Headers values can be one of: int, float, str, list, tuple, or list(tuple).
        - floats are printed with the number of significan digit specified by the gloabal variable PRECISION.
        - list elements are printed with the same headers key.
        - coefficients, directions and corrections items need to be stored as tuple for the correct formatting
          field width of 12 and 8 decimals precision.
    """

    def __init__(self):
        self.odf = HEADERS_DEFAULT["odf"].copy()
        self.cruise = HEADERS_DEFAULT["cruise"].copy()
        self.event = HEADERS_DEFAULT["event"].copy()
        self.buoy = HEADERS_DEFAULT["buoy"].copy()
        self.plankton = HEADERS_DEFAULT["plankton"].copy()
        self.meteo = HEADERS_DEFAULT["meteo"].copy()
        self.instrument = HEADERS_DEFAULT["instrument"].copy()
        self.quality = HEADERS_DEFAULT["quality"].copy()
        self.record = HEADERS_DEFAULT["record"].copy()
        self.buoy_instrument = dict()
        self.general_cal = dict()
        self.polynomial_cal = dict()
        self.compass_cal = dict()
        self.history = dict()
        self.parameter = dict()
        self.data = pd.DataFrame()

    def __repr__(self):
        s = "<odf_format.ODF>" + NEWLINE
        s += "headers:" + NEWLINE

        for h in list(HEADERS_DEFAULT.keys()):
            if h in self.__dict__:
                if any(self.__dict__[h].values()):
                    s += h + NEWLINE
                else:
                    s += h + "(empty)" + NEWLINE

        for h in REPEATED_HEADERS:
            if self.__dict__[h]:
                s += h + f" ({len(self.__dict__[h])})" + NEWLINE
            else:
                s += h + " (empty)" + NEWLINE

        s += "data:" + NEWLINE
        if self.data.empty:
            s += SPACE + "(empty)" + NEWLINE

        else:
            s += SPACE + f"pandas.Dataframe of shape {self.data.shape}"

        return s

    def read(self, filename: str):
        """Read ODF files.
        The ODF headers section in nested dictionnaries in ODF.headers and
        ODF.parameters. The data is store in a pandas.DataFrame.

        Notes
        -----
        All items values are stored in list. After all the headers are read, list of lenght one
        are converted to int, float or str.

        Calibration coefficients, directions and corrections are stored in tuple.
        """
        self.__init__()
        is_data = False
        current_header = None
        header_key = ""
        header_type = ""
        parameters_code = []
        counters = dict(
            parameter=0,
            buoy_instrument=0,
            general_cal=0,
            polynomial_cal=0,
            compass_cal=0,
            history=0,
        )
        with open(filename, "r", encoding="ISO-8859-1") as f:
            while not is_data:
                line = f.readline().split(",")[0]

                if not line:
                    break

                if line.startswith("  "):
                    key, item = _get_key_and_item(line)
                    if key in current_header:
                        if isinstance(current_header[key], list):
                            current_header[key].append(item)
                        else:
                            current_header[key] = [item]
                    else:
                        current_header[key] = [item]

                elif " -- DATA --" in line:
                    is_data = True

                elif any([h.upper() + "_HEADER" in line for h in REPEATED_HEADERS]):
                    for h in REPEATED_HEADERS:
                        if h.upper() + "_HEADER" in line:
                            header_key = h + "_" + str(counters[h])
                            counters[h] += 1
                            self.__dict__[h][header_key] = REPEATED_HEADERS_DEFAULT[
                                h
                            ].copy()
                            current_header = self.__dict__[h][header_key]

                else:
                    header_key = "_".join(line.split("_")[:-1]).lower()
                    current_header = self.__dict__[header_key]

            for _, section in self.__dict__.items():
                _reshape_header(section)

            for p in list(self.parameter.keys()):
                code = self.parameter[p]["code"]
                self.parameter[code] = self.parameter.pop(p)

                parameters_code.append(code)

            for bi in list(self.buoy_instrument.keys()):
                name = self.buoy_instrument[bi]["name"]
                self.buoy_instrument[name] = self.buoy_instrument.pop(bi)

            for cal_headers in ["general_cal", "polynomial_cal", "compass_cal"]:
                for cal in list(self.__dict__[cal_headers].keys()):
                    code = self.__dict__[cal_headers][cal]["code"]
                    self.__dict__[cal_headers][code] = self.__dict__[cal_headers].pop(
                        cal
                    )

            if is_data:
                self.data = pd.read_csv(
                    f,
                    names=parameters_code,
                    decimal=".",
                    delim_whitespace=True,
                    quotechar="'",
                )
            else:
                print("Data section not found in ODF")

        return self

    def save(self, filename: str):
        """ """
        filename = Path(filename).with_suffix(".ODF")
        with open(filename, "w+", encoding="ISO-8859-1") as f:
            f.write(self._headers_string_format())
            f.write(SPACE + "-- DATA --" + NEWLINE)
            self._write_data(buf=f)

    def to_dataset(self, dims: tp.Union[str, tp.List[str]] = None, time: str = None):
        """
        Parameters
        ----------
        dims :
           Dimensions names.
        time :
            Specify wich dimensions is time.
        """
        if time:
            self.data[time] = pd.to_datetime(self.data[time])

        if dims:
            data = self.data.set_index(dims)
        else:
            data = self.data

        dataset = xr.Dataset.from_dataframe(data)

        for p in self.parameter:
            dataset[p].assign_attrs(self.parameter[p])

        history = {}
        for i, h in zip(range(len(self.history)), self.history):
            cd = [self.history[h]["creation_date"]]
            process = self.history[h]["process"]
            if not isinstance(process, list):
                process = [process]
            history = {f"process_{i}": "\n".join(cd + process)}

        dataset.attrs = {
            **self.event,
            **self.cruise,
            **self.buoy,
            **self.instrument,
            **history,
        }

        return dataset

    def add_polynomial_cal(self, code: str, items: dict):
        """Add a polynomial cal headers to ODF.polynomial_cal

        Parameters
        ----------
        code :
            Name(key) for the parameter code.
        items :
            Dictionnary containing parameter header items.
        """
        self.polynomial_cal[code] = REPEATED_HEADERS_DEFAULT["polynomial_cal"].copy()
        self.polynomial_cal[code]["code"] = code
        self.polynonial_cal[code].update(items)

    def add_general_cal(self, code: str, items: dict = {}):
        """Add a general cal headers to ODF.general_cal

        Parameters
        ----------
        code :
            Name(key) for the parameter code.
        items:
            Dictionnary containing parameter header items.
        """
        self.general_cal[code] = REPEATED_HEADERS_DEFAULT["general_cal"].copy()
        self.general_cal[code]["code"] = code
        self.general_cal[code].update(items)

    def add_compass_cal(self, code: str, items: dict = {}):
        """Add a compass cal headers to ODF.compass_cal

        Parameters
        ----------
        code :
            Name(key) for the parameter code.
        """
        self.compass_cal[code] = REPEATED_HEADERS_DEFAULT["compass_cal"].copy()
        self.compass_cal[code]["code"] = code
        self.compass_cal[code].update(items)

    def add_buoy_instrument(self, name: str, items: dict = {}):
        """Add a buoy instrument headers to ODF.instruments.

        Parameters
        ----------
        name :
            Name(key) for the instrument header.
        items :
            Dictionnary containing parameter header items.
        """
        self.buoy_instrument[name] = REPEATED_HEADERS_DEFAULT["buoy_instrument"].copy()
        self.buoy_instrument[name]["name"] = name
        self.buoy_instrument[name].update(items)

    def add_parameter(
        self,
        code: str,
        data: tp.Union[list, tp.Type[np.ndarray]],
        items: dict = {},
        null_value=None,
    ):
        """Add a the parameter to ODF.parameters and the data to ODF.data.

        Computes `number_valid`, `number_null`, `minimum_value` and `maximum_value` from
        the data and a provided null_value.

        Parameters
        ----------
        code :
            Name(key) for the parameter code.
        data :
            1-D sequence of data. Each parameters must have the same length.

        null_value :
           Value used for missing or null value in data. From this value `number_valid`,
           `number_null` will be computed.
        items :
            Dictionnary containing parameter header items.


        """
        self.parameter[code] = REPEATED_HEADERS_DEFAULT["parameter"].copy()
        self.parameter[code]["code"] = code
        self.parameter[code].update(items)
        self.data[code] = data

        self._compute_parameter_attrs(code, null_value)

    def add_history(self, items: dict):
        """"""
        header_name = "history_" + str(len(self.history) + 1)
        self.history[header_name] = REPEATED_HEADERS_DEFAULT["history"].copy()
        self.history[header_name].update(items)
        if not self.history[header_name]["creation_date"]:
            self.history[header_name]["creation_date"] = (
                pd.Timestamp.now().strftime("%d-%b-%Y %H:%M:%S.%f").upper()[:-4]
            )

    def from_dataframe(
        self,
        dataframe: tp.Type[pd.DataFrame],
        items: dict = {},
        null_values: tp.Union[int, float, list, tuple, dict] = None,
    ):
        """Add data and parameters from a pandas.dataframe. Collumns names are used for
        the new parameters code.

        Paramters
        ---------
        dataframe :
            The data to be added to the ODF. All data must be 1 dimensional.

        null_values :
            Value used for missing or null value in data. From this value `number_valid`,
            `number_null` will be computed. If a single value is provided, it will be
            applied to all the data. A dictionnary of with matching keys matching dataframe
            collumns or list and tuple can be pass with different null_value but all null_value
            must have the same length as the number of collumns in the dataframe.
        items :
            Dictionnary containing parameter header items. Keys must be the parameters code.

        """
        if isinstance(dataframe, pd.DataFrame):
            dataframe = dataframe.reset_index(drop=True)
        else:
            raise TypeError("dataframe must be a pandas.DataFrame")
        for code in dataframe.columns:
            self.parameter[code] = REPEATED_HEADERS_DEFAULT["parameter"].copy()
            self.parameter[code]["parameter"] = code
            if code in items:
                self.parameter[code].update(items[code])

        if self.data.empty:
            self.data = dataframe
        else:
            self.data.merge(dataframe)

        if isinstance(null_values, (float, int)) or null_values:
            null_values = dict.fromkeys(dataframe.columns, null_values)
        elif isinstance(null_values, (list, tuple)):
            if len(null_values) != len(dataframe.columns):
                raise ValueError(
                    f"null_values lenght ({len(null_values)}) doesn't match"
                    + " the number of collumns ({len(dataframe.columns)})in the dataframe."
                )
            else:
                null_values = dict(zip(dataframe.columns, null_values))
        else:
            null_values = dict.fromkeys(dataframe.columns, null_values)
            for key, item in items.items():
                if "null_value" in item:
                    null_values[key] = item["null_value"]

        for code in dataframe.columns:
            self._compute_parameter_attrs(code, null_values[code])

        self.record = self._make_record()

        return self

    def _compute_parameter_attrs(self, parameter: str, null_value=None):
        """Compute `number_valid`, `number_null`, `minimum_value` and `maximum_value` from
        the data."""
        n_null = (self.data[parameter] == null_value).sum().item()
        self.parameter[parameter]["null_value"] = null_value
        self.parameter[parameter]["number_null"] = n_null
        self.parameter[parameter]["number_valid"] = len(self.data[parameter]) - n_null
        self.parameter[parameter]["minimum_value"] = (
            self.data[parameter].where(self.data[parameter] != null_value).min()
        )
        self.parameter[parameter]["maximum_value"] = (
            self.data[parameter].where(self.data[parameter] != null_value).max()
        )

    def _headers_string_format(self):
        s = ""
        for h in ["odf", "cruise", "event", "buoy", "plankton", "meteo", "instrument"]:
            if h in self.__dict__:
                if any(self.__dict__[h].values()):
                    s += _format_headers(h, self.__dict__[h])

        for name, header in self.buoy_instrument.items():
            s += _format_headers("buoy_instrument", header)

        if any(self.__dict__["quality"].values()):
            s += _format_headers("quality", self.__dict__["quality"])

        for h in ["general_cal", "polynomial_cal", "compass_cal", "history"]:
            for name, header in self.__dict__[h].items():
                s += _format_headers(h, header)

        for name, header in self.parameter.items():
            s += _format_headers("parameter", header)

        s += _format_headers("record", self._make_record())

        return s

    def _make_record(self):
        return dict(
            num_calibration=len(self.polynomial_cal),
            num_swing=len(self.compass_cal),
            num_history=len(self.history),
            num_cycle=len(self.data),
            num_param=len(self.parameter),
        )

    def _write_data(self, buf):
        """Write data to a buffer.

        See pandas.DataFrame.to_string

        """
        index_names = list(self.data.index.names)
        self.data.reset_index(inplace=True, drop=True)
        valid_data = []
        for key in self.parameter:
            if key in self.data.keys():
                valid_data.append(key)

        data = self.data[valid_data]
        formats = {}
        for vd in valid_data:
            padding = self.parameter[vd]["print_field_width"]
            decimal_places = self.parameter[vd]["print_decimal_places"]
            if self.data[vd].dtype == int:
                formats[vd] = lambda x, p=padding: SPACE + str(x).rjust(p, SPACE)

            elif any(self.data[vd].dtypes == t for t in [int, object]):
                formats[vd] = lambda x, p=padding: (
                    SPACE + ("'" + str(x) + "'").rjust(p, SPACE)
                )

            elif self.data[vd].dtypes == np.dtype("<M8[ns]"):
                formats[vd] = lambda x, p=padding: (
                    SPACE + (x.strftime("%d-%b-%Y %H:%M:%S.%f").upper()).rjust(p, SPACE)
                )

            else:
                formats[vd] = lambda x, p=padding, d=decimal_places: (
                    SPACE + (f"{x:.{d}f}").rjust(p, SPACE)
                )

        self.data.to_string(
            buf=buf,
            formatters=formats,
            header=False,
            index=False,
            na_rep=NA_REP,
        )


def _format_headers(name: str, header: dict) -> str:
    s = name.upper() + "_HEADER," + NEWLINE
    for key, value in header.items():
        if isinstance(value, str):
            s += INDENT + key.upper() + " = " + f"'{value}'," + NEWLINE
        elif isinstance(value, int):
            s += INDENT + key.upper() + " = " + f"{value}," + NEWLINE
        elif isinstance(value, float):
            s += INDENT + key.upper() + " = " + f"{value:.{PRECISION}f}," + NEWLINE
        elif isinstance(value, list):
            parent = INDENT + f"{key.upper()} = "
            s += _format_list(value, parent)
        elif isinstance(value, tuple):
            s += (
                INDENT
                + key.upper()
                + " = "
                + "".join([f"{v:{12}.{8}f}" for v in value])
                + ","
                + NEWLINE
            )
        else:
            print("Could not format", name, key, value)

    return s


def _format_list(_list: list, parents: str) -> str:
    s = ""
    if len(_list) == 0:
        s += parents + "'" + f"," + NEWLINE
        return s
    else:
        for value in _list:
            if isinstance(value, tuple):
                s += (
                    parents
                    + " ".join([f"{v:{12}.{8}f}" for v in value])
                    + ","
                    + NEWLINE
                )
            else:
                s += parents + "'" + f"{value}'," + NEWLINE
        return s


def _get_key_and_item(line):
    """ Return key and item from a line"""
    key, item = line.split("=", 1)
    key, item = key.strip().lower(), item.strip()
    if not item:
        pass
    elif not any(char in item for char in [":", "'", " "]):
        item = eval(item)
    else:
        item = item.strip().strip("'")
    return key, item


def _reshape_header(header):
    """Replace list of length one by the single element it contain.

    Elements of items with keys named `coefficients`, `directions` or `corrections` are
    split into tuple of and are evaluated.

    """
    for key, item in header.items():
        if isinstance(item, dict):
            _reshape_header(item)

        elif isinstance(item, list):
            if any(key == c for c in ["coefficients", "directions", "corrections"]):
                for i in range(len(item)):
                    header[key][i] = tuple(map(eval, header[key][i].split()))
            if len(item) == 1:
                header[key] = item[0]


if __name__ == "__main__":

    import matplotlib.pyplot as plt

    path = [
        # "/home/jeromejguay/ImlSpace/Docs/ODF/Format_ODF/Exemples/CTD_BOUEE2019_RIKI_04130218_DN",
        "/home/jeromejguay/ImlSpace/Docs/ODF/Format_ODF/Exemples/MADCP_BOUEE2019_RIMOUSKI_553_VEL",
        #        "/home/jeromejguay/ImlSpace/Docs/ODF/Format_ODF/Exemples/MMOB_BOUEE2019_RIMOUSKI_IML4_METOCE",
        #        "/home/jeromejguay/ImlSpace/Docs/ODF/Format_ODF/Exemples/MADCP_BOUEE2019_RIMOUSKI_553_ANC",
    ]

    P = 0
    test_count = 5
    odf = Odf()
    print("Running odf test ...")
    print(f"Test file = {path[0]}.ODF")

    print("Reading from ODF", end=" ... ")
    try:
        odf.read(path[0] + ".ODF")
        print("Passed")
        P += 1
        print("Saving to ODF", end=" ... ")
        try:
            odf.save("odf_to_odf_test.ODF")
            print("Passed")
            P += 1
        except Exception:
            print("Failed")

        print("From Dataframe", end=" ... ")
        dataframe = odf.data
        items = {key: item for key, item in odf.parameter.items()}
        try:
            from_df = Odf().from_dataframe(dataframe, items)
            print("Passed")
            P += 1
        except Exception:
            print("Failed")

        print("ODF to dataset", end=" ... ")
        try:
            dataset = odf.to_dataset(dims=["SYTM_01", "DEPH_01"], time="SYTM_01")
            print("Passed")
            P += 1

            print("Dataset to netcdf", end=" ... ")
            try:
                dataset.to_netcdf("odf_to_nc_test.nc")
                print("Passed")
                P += 1
            except Exception:
                print("Failed")

        except Exception:
            print("Failed")
    except Exception:
        print("Failed")

    print(f"Test Finished. Passed:{P}/{test_count}")
