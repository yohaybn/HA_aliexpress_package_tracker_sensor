  

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

Removes an existing package tracking numbers.

**Service Data:**

-   `tracking_number` (optional): The tracking number of the package to remove.
-   `entity_id` (optional): list of entity_id's of sensor to remove.

**Examples:**



```YAML
action: aliexpress_package_tracker.remove_tracking
data:
    tracking_number: "LP123456789CN"

```



```YAML
action: aliexpress_package_tracker.remove_tracking
data:
    entity_id:
        - sensor.aliexpress_package_no_ae123456789
        - sensor.aliexpress_package_no_rs123456789y

```

### `aliexpress_package_tracker.edit_title`

Edit existing title.

**Service Data:**

-   `entity_id` (required): The entity_id of sensor.
-   `new_title` (required): A custom title for the package. Defaults to "Package".

**Example:**



```YAML
action: aliexpress_package_tracker.edit_title
data:
    entity_id: sensor.aliexpress_package_no_ae123456789
    new_title: New Title

```

## Lovelace Example

**Recommended: Use the dedicated AliExpress Package Card for an enhanced experience!**

For a more visually appealing and feature-rich display of your AliExpress package tracking information, consider using the dedicated Lovelace card: [lovelace-aliexpress-package-card](https://github.com/yohaybn/lovelace-aliexpress-package-card)

![AliExpress Package Card](https://github.com/yohaybn/lovelace-aliexpress-package-card/blob/main/images/screenshot_light.png)
![AliExpress Package Card](https://github.com/yohaybn/lovelace-aliexpress-package-card/blob/main/images/screenshot_dark.png)

 

**Alternatively, create a Markdown card using the following code:**



```Markdown
type: markdown
content: >-
    {% for sens in integration_entities("aliexpress_package_tracker") %}
    {% set entity = states[sens] %}
    >- {% if "carrier_url" in entity.attributes-%}[<ha-icon icon="mdi:information-outline"></ha-icon>]({{entity.attributes.carrier_url}}){%endif %} **{{ entity.attributes.title }} ({{
    entity.attributes.order_number }}{% if "realMailNo" in entity.attributes-%}
        / {{entity.attributes.realMailNo }}
    {%- endif %}):**
    {% if "last_update_status" in entity.attributes-%}
        {{entity.attributes.last_update_status }}
    {%- endif %}
    {% if "daysNumber" in entity.attributes-%}  In Transit: {{entity.attributes.daysNumber  }}{%- endif %}
    {% endfor %}

```

## Automation Example - Add Package Based on Email

### Setup IMAP Integration

1.  Set up the [IMAP integration](https://www.home-assistant.io/integrations/imap/).
2.  Create a sensor for email content named "post_track".

<!-- end list -->


```YAML
# configuration.yaml
template:
    - sensor:
      - name: post_track
        state: '{{ trigger.event.data["subject"] }}'
        attributes:
          body: "{{ trigger.event.data['text'] }}"
      trigger:
      - event_data:
          custom: true    # See example here [https://www.home-assistant.io/integrations/imap/#example---custom-event-data-template](https://www.home-assistant.io/integrations/imap/#example---custom-event-data-template) how to set it up
        event_type: imap_content
        id: custom_event
        trigger: event
```

### Create Tracking Number Sensors



```YAML
# configuration.yaml
sensor:
    - platform: template
        sensors:
            new_tracking_number_body:
                value_template: "{{ state_attr('sensor.post_track','body') | base64_decode | regex_findall_index('(([A-Z]){2}([0-9]){9,10}([A-Z]){0,2})')|first }}"
            new_tracking_number_subject:
                value_template: "{{ state_attr('sensor.post_track','subject') | regex_findall_index('(([A-Z]){2}([0-9]){9,10}([A-Z]){0,2})')|first  }}"

```

### Create Automation

```YAML
# automation.yaml
  - alias: track package when get email
    trigger:
        - platform: state
            entity_id:
                - sensor.new_tracking_number_subject
            id: "subject"
        - platform: state
            entity_id:
                - sensor.new_tracking_number_body
            id: "body"
    variables:
        src: "sensor.new_tracking_number_{{trigger.id}}"
    condition: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] and (states(src) !='unknown' )}}"
    action:
        - service: aliexpress_package_tracker.add_tracking
          data:
            tracking_number: "{{states(src)}}"
    mode: single

```

## Automation Example- Notify on AliExpress Package Update

This automation sends a notification to your mobile app when any AliExpress package tracking information is updated.



```YAML
  - alias: Notify on AliExpress Package Update
    triggers:
        - trigger: event
            event_type: aliexpress_package_data_updated
    actions:
        - service: notify.mobile_app_my_phone
          data:
            title: "AliExpress Package Update"
            message: >-
                Package {{ trigger.event.data.entity_id }} has been updated.
                Old State: {{ trigger.event.data.old_state | default('Unknown') }}.
                New State: {{ trigger.event.data.new_state | default('Unknown') }}.
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
