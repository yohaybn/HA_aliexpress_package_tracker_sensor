

# HA_aliexpress_package_tracker_sensor
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

This Home Assistant custom component provides sensor entities to track your packages from AliExpress using Cainiao Global tracking. It allows you to add and remove tracking numbers via Home Assistant services and provides detailed package status information.

## Features

-   **Tracking Package Status:** Displays the current status of your AliExpress packages.
-   **Service Calls:**
    -   `aliexpress_package_tracker.add_tracking`: Adds a new tracking number.
    -   `aliexpress_package_tracker.remove_tracking`: Removes an existing tracking number.
-   **Automatic Updates:** Periodically updates package information.
-   **Storage:** Persists tracking numbers across Home Assistant restarts.
-   **Duplicate Tracking Number Handling:** Automatically resolves and merges duplicate tracking numbers.
-   **Real Tracking Number Extraction:** Extracts the real tracking number from Cainiao data.
-   **Order URL Generation:** Generates direct order URLs from tracking data if exists.
-   **Event Firing:** Fires a custom event (`aliexpress_package_data_updated`) on state changes.

## Installation

1.  **HACS (Recommended):**
    -   Add this repository as a custom repository in HACS.
    -   Install the "AliExpress Package Tracker" integration.
2.  **Manual Installation:**
    -   Copy the `custom_components/aliexpress_package_tracker` directory into your Home Assistant `custom_components` directory.
    -   Restart Home Assistant.

## Configuration

1.  Go to **Settings** -> **Devices & Services**.
2.  Click **Add Integration** and search for "AliExpress Package Tracker".
3.  Follow the configuration steps.

## Services

### `aliexpress_package_tracker.add_tracking`

Adds a new package tracking number.

**Service Data:**

-   `tracking_number` (required): The tracking number of the package.
-   `title` (optional): A custom title for the package. Defaults to "Package".

**Example:**

```yaml
service: aliexpress_package_tracker.add_tracking
data:
  tracking_number: "LP123456789CN"
  title: "My New Gadget"

```

### `aliexpress_package_tracker.remove_tracking`

Removes an existing package tracking number.

**Service Data:**

-   `tracking_number` (required): The tracking number of the package to remove.

**Example:**



```YAML
service: aliexpress_package_tracker.remove_tracking
data:
  tracking_number: "LP123456789CN"

```

## Lovelace Example



```Markdown

type: markdown
content: >-
 {% for sens in integration_entities("aliexpress_package_tracker")  %}
  {% set entity = states[sens] %}
  >- {% if "carrier_url" in entity.attributes-%}[<ha-icon icon="mdi:information-outline"></ha-icon>]({{entity.attributes.carrier_url}}){%endif %} **{{ entity.attributes.title }} ({{
entity.attributes.order_number }}{% if "realMailNo" in entity.attributes-%}
  / {{entity.attributes.realMailNo }}
{%- endif %}):**
{% if "last_update_status" in entity.attributes-%}
  {{entity.attributes.last_update_status }}
{%- endif %}
{% if "daysNumber" in entity.attributes-%}   In Transit: {{entity.attributes.daysNumber   }}   {%- endif %}
{% endfor %}
  {% endfor %}

```

## Automation Example (Add Package Based on Email)

### Setup IMAP Integration

1.  Set up the [IMAP integration](https://www.home-assistant.io/integrations/imap/).
2.  Create a sensor for email content named "post_track".



```YAML
# configuration.yaml
template:
  - sensor:
      - name: post_track
        state: "{{ trigger.event.data['subject'] }}"
        attributes:
          body: "{{ trigger.event.data['text'] }}"
        trigger:
          - event_data:
              custom: true # See example here [https://www.home-assistant.io/integrations/imap/#example---custom-event-data-template](https://www.home-assistant.io/integrations/imap/#example---custom-event-data-template) how to set it up
            event_type: imap_content
            id: custom_event
            platform: event

```

### Create Tracking Number Sensors



```YAML
# configuration.yaml
sensor:
  - platform: template
    sensors:
      new_tracking_namber_body:
        value_template: "{{ state_attr('sensor.post_track','body') | base64_decode | regex_findall_index('(([A-Z]){2}([0-9]){9,10}([A-Z]){0,2})')|first }}"
      new_tracking_namber_subject:
        value_template: "{{ state_attr('sensor.post_track','subject') | regex_findall_index('(([A-Z]){2}([0-9]){9,10}([A-Z]){0,2})')|first  }}"

```

### Create Automation

```YAML
# automation.yaml
- alias: track package when get email
  trigger:
    - platform: state
      entity_id:
        - sensor.new_tracking_namber_subject
      id: "subject"
    - platform: state
      entity_id:
        - sensor.new_tracking_namber_body
      id: "body"
  variables:
    src: "sensor.new_tracking_namber_{{trigger.id}}"
  condition: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] and (states(src) !='unknown' )}}"
  action:
    - service: aliexpress_package_tracker.add_tracking
      data:
        tracking_number: "{{states(src)}}"
  mode: single

```

## Important Notes

-   This component relies on the Cainiao Global tracking API.
-   The component handles duplicate tracking numbers by merging their titles.
-   The component extracts the real tracking number to ensure accurate tracking.
-   The component fires a custom event (`aliexpress_package_data_updated`) whenever a package's state changes.

## Contributing

Feel free to contribute to this project by submitting pull requests or reporting issues.


### Donate
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/yohaybn)

If you find it helpful or interesting, consider supporting me by buying me a coffee or starring the project on GitHub! ☕⭐
Your support helps me improve and maintain this project while keeping me motivated. Thank you! ❤️
