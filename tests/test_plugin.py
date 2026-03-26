"""
Placeholder
"""
import os
from tests.shared import APIBase
import httpx
import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

BASE_PATH = os.getenv('BASE_PATH')
PLUGIN_ID = os.getenv("PLUGIN_ID")

# ===================================== Plugin Actions =====================================
class TestPluginActions(APIBase):

    @classmethod
    def setUpClass(cls):
        pass

    @staticmethod
    def _execute_action(action_id: str, deviceId: int = 0, props: dict = None, wait: bool = True, msg_id: str = "test-plugin-action", timeout: float = 5.0) -> bool | httpx.Response:
        """Post a plugin.executeAction command to the Indigo Web Server API.

        Args:
            action_id (str): The Indigo action ID to execute.
            props (dict): Optional action props to include in the payload.
            wait (bool): Whether to wait for the action to complete before returning.
            msg_id (str): Value for the message ``id`` field, used to identify the call in logs.
            timeout (float): HTTP request timeout in seconds.

        Returns:
            bool | httpx.Response: The HTTP response, or False if the request failed.
        """
        try:
            message: dict = {
                "id":            msg_id,
                "message":       "plugin.executeAction",
                "pluginId":      os.getenv("PLUGIN_ID"),
                "actionId":      action_id,
                "waitUntilDone": wait,
            }
            if deviceId != 0:
                message["deviceId"] = deviceId
            if props is not None:
                message["props"] = props
            url = f"{os.getenv('URL_PREFIX')}/v2/api/command/?api-key={os.getenv('GOOD_API_KEY')}"
            return httpx.post(url, json=message, verify=False, timeout=timeout)
        except Exception:
            return False

    def _assert_response(self, result: bool | httpx.Response, msg: str) -> httpx.Response:
        """Assert that the result is a valid HTTP response, not a failed request.

        Args:
            result (bool | httpx.Response): The result from _execute_action.
            msg (str): Assertion failure message.

        Returns:
            httpx.Response: The validated response object.
        """
        self.assertIsInstance(result, httpx.Response, f"Request failed with exception: {msg}")
        return result

    def test_refresh_csv_device_action(self):
        """Verify refresh_csv_device runs successfully."""
        config = {"targetDevice": os.getenv("REFRESH_CSV_ACTION")}
        result = self._assert_response(
            self._execute_action("refresh_csv_device", props=config, wait=True),
            "action_refresh_the_charts failed"
        )
        self.assertEqual(result.status_code, 200, f"Action call failed.")

    def test_refresh_csv_source_action(self):
        """Verify refresh_csv_source runs successfully."""
        config = {"targetDevice": os.getenv("REFRESH_CSV_TARGET_DEVICE"), "targetSource": os.getenv("REFRESH_CSV_TARGET_SOURCE")}
        result = self._assert_response(
            self._execute_action("refresh_csv_source", props=config, wait=True),
            "action_refresh_the_charts failed"
        )
        self.assertEqual(result.status_code, 200, f"Action call failed.")

    def test_refresh_a_chart_action(self):
        """Verify refreshAChartAction runs successfully."""
        result = self._assert_response(
            self._execute_action("refreshAChartAction",
                                 deviceId=int(os.getenv("REDRAW_A_CHART_ACTION")),
                                 wait=True),
            "action_refresh_the_charts failed"
        )
        self.assertEqual(result.status_code, 200, f"Action call failed.")

    def test_action_refresh_the_charts(self):
        """Verify refreshAChartAction runs successfully."""
        result = self._assert_response(
            self._execute_action("action_refresh_the_charts",
                                 wait=True,
                                 timeout=60.0),
            "action_refresh_the_charts failed"
        )
        self.assertEqual(result.status_code, 200, f"Action call failed.")

    def test_themeApplyAction(self):
        """Verify themeApplyAction runs successfully."""
        config = {"targetTheme": os.getenv("APPLY_THEME")}
        result = self._assert_response(
            self._execute_action("themeApplyAction", props=config, wait=True),
            "themeApplyAction failed"
        )
        self.assertEqual(result.status_code, 200, f"Action call failed.")

# ===================================== Menu Items =====================================
    # TODO: combine disable/enable into one test, take a snapshot of current enabled states and restore that global
    #  state when test is done.
    def test_comms_kill_all_menu(self):
        """Verify comms_kill_all runs successfully."""
        result = self._assert_response(
            self._execute_action("comms_kill_all", wait=True),
            "comms_kill_all menu item failed"
        )
        self.assertEqual(result.status_code, 200, f"Menu item call failed.")

    def test_comms_unkill_all_menu(self):
        """Verify comms_unkill_all runs successfully."""
        result = self._assert_response(
            self._execute_action("comms_unkill_all", wait=True),
            "comms_unkill_all menu item failed"
        )
        self.assertEqual(result.status_code, 200, f"Menu item call failed.")

    def test_print_environment_info_menu(self):
        """Verify print_environment_info runs successfully."""
        result = self._assert_response(
            self._execute_action("print_environment_info", wait=True),
            "print_environment_info menu item failed"
        )
        self.assertEqual(result.status_code, 200, f"Menu item call failed.")

    def test_refresh_the_charts_now_menu(self):
        """Verify refresh_the_charts_now runs successfully."""
        config = {"allCharts": "all"}
        result = self._assert_response(
            self._execute_action("refresh_the_charts_now", props=config, wait=True),
            "refresh_the_charts_now menu item failed"
        )
        self.assertEqual(result.status_code, 200, f"Menu item call failed.")

    def test_save_snapshot_menu(self):
        """Verify saveSnapshot runs successfully."""
        result = self._assert_response(
            self._execute_action("saveSnapshot", wait=True),
            "saveSnapshot menu item failed"
        )
        self.assertEqual(result.status_code, 200, f"Menu item call failed.")
