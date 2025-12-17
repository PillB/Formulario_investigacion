from datetime import datetime

from utils.historical_consolidator import append_historical_records


def test_append_historical_records_creates_and_appends(tmp_path):
    header = ["id_cliente", "id_caso"]
    rows = [{"id_cliente": "=CL1", "id_caso": "2024-0001"}]
    timestamp = datetime(2024, 1, 1, 12, 0, 0)

    first_path = append_historical_records(
        "clientes", rows, header, tmp_path, "2024-0001", timestamp=timestamp
    )
    second_rows = [{"id_cliente": "CL2", "id_caso": "2024-0001"}]
    second_path = append_historical_records(
        "clientes", second_rows, header, tmp_path, "2024-0001", timestamp=timestamp
    )

    assert first_path == second_path == tmp_path / "h_clientes.csv"
    contents = (tmp_path / "h_clientes.csv").read_text(encoding="utf-8").splitlines()
    assert contents[0].split(",") == ["id_cliente", "id_caso", "case_id", "fecactualizacion"]

    data_lines = contents[1:]
    assert len(data_lines) == 2
    first_columns = data_lines[0].split(",")
    assert first_columns[0] == "'=CL1"
    assert first_columns[2] == "2024-0001"
    assert first_columns[3] == "2024-01-01T12:00:00"

    second_columns = data_lines[1].split(",")
    assert second_columns[0] == "CL2"
    assert second_columns[2] == "2024-0001"
    assert second_columns[3] == "2024-01-01T12:00:00"
