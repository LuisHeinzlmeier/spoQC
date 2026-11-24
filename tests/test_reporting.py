import pytest

from spoqc.reporting import configure_plots, plots_enabled, plots_only


def test_plots_default_and_override():
    @plots_only
    def render():
        return "figure"

    @configure_plots
    def run():
        return render()

    assert run() == "figure"
    assert run(plots=False) is None
    assert run() == "figure"


def test_plot_setting_restored_after_error():
    @configure_plots
    def run():
        assert not plots_enabled()
        raise RuntimeError

    with pytest.raises(RuntimeError):
        run(plots=False)

    assert plots_enabled()
