  

# HA_aliexpress_package_tracker_sensor
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

This Home Assistant custom component provides sensor entities to track your packages from AliExpress using Cainiao Global tracking. It allows you to add and remove tracking numbers via Home Assistant services and provides detailed package status information.

**This integration now includes the Custom Lovelace Card automatically!**
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
-   **Built-in Lovelace Card**: Includes a beautiful custom card to display your packages without extra installation.

## Donate
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/yohaybn)

If you find it helpful or interesting, consider supporting me by buying me a coffee or starring the project on GitHub! ☕⭐
Your support helps me improve and maintain this project while keeping me motivated. Thank you! ❤️

## Installation

1.  **HACS (Recommended):**
    
    -   Install the "AliExpress Package Tracker" integration from HACS.
    -   Restart Home Assistant.

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

## Lovelace Card

**Note:** You **do not** need to install the `lovelace-aliexpress-package-card` separately. It is now automatically installed and registered when you install this integration!
```yaml
type: custom:aliexpress-package-card
# Optional Configuration
title: AliExpress Packages  # Custom title for the card
hide_add_tracking: false    # Set to true to hide the 'Add Tracking' input field
exclude_attributes:       # Optional: List of attributes to hide from the card
#   - order_number
#   - status
#   - last_update_time
#   - last_update_status
#   - progressStatus
#   - carrier
#   - carrier_url
#   - daysNumber
#   - orignal_track_id
#   - order_url
```

![AliExpress Package Card](https://github.com/yohaybn/lovelace-aliexpress-package-card/blob/main/images/screenshot_light.png)
![AliExpress Package Card](https://github.com/yohaybn/lovelace-aliexpress-package-card/blob/main/images/screenshot_dark.png)


### Credits

Special thanks to the following projects for the method used to automatically register the Lovelace card resources without requiring manual installation:
*   [ArikShemesh/ha-simple-timer](https://github.com/ArikShemesh/ha-simple-timer)
*   [davidss20/home-assistant-24h-timer-integration](https://github.com/davidss20/home-assistant-24h-timer-integration)

  
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

## 🌍 Localization / Translations

This card supports displaying text in multiple languages using translation files located in the translations/ directory.

**How it Works:**

-   Each supported language has a JSON file (e.g., en.json, es.json).
    
-   The card uses English (en.json) as the default and fallback language. If a translation is missing in your selected language, it will display the English text instead.
    
-   An index.json file lists the available languages for selection in the card's editor.
    

**🙏 Help Improve Translations!**

The current non-English translations were generated using AI and **may contain errors or sound unnatural**. We rely on the community to improve them!

**How to Contribute:**

1.  **Find the translations/ folder** in the [card's source directory](https://github.com/yohaybn/HA_aliexpress_package_tracker_sensor/tree/main/custom_components/aliexpress_package_tracker/dist).
    
2.  **Copy en.json** and **rename** it using the [ISO 639-1 code](https://www.google.com/url?sa=E&q=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FList_of_ISO_639-1_codes) for your language (e.g., pt.json for Portuguese).
    
3.  **Translate** the **string values** (text after the colons) in your new file. **Do not change the keys** (text before colons). Use a UTF-8 compatible editor.
    
4.  **Add your language** to translations/index.json, following the existing format (e.g., { "code": "pt", "name": "Português" }).
    
5.  **Submit** your changes via a Pull Request or GitHub Issue on the card's repository.
    

Your contributions help make this card better for everyone!

## 🚚 Carrier Logos

This card displays carrier logos for easier visual identification.

**How it Works:**
-   Logos are mapped from carrier names to image URLs in the `carrier_logos.json` file.  
-   If a logo isn't in the file, the card attempts to use the carrier's website favicon as a fallback (requires carrier_url attribute).
    

**🙏 Help Expand Logo Coverage!**
The included logo list might be incomplete. Adding logos for more carriers benefits everyone.
**How to Contribute:**
1.  **Find** a public URL for the missing carrier's logo.
2.  **Add** an entry to carrier_logos.json, mapping the exact carrier name (from attributes) to the logo URL. 
    ```
    // carrier_logos.json - Example Addition
    {
      // ... existing logos ...
      "Specific Carrier Name": "https://carrier.com/logo.png"
    }
    ```
    
3.  **Submit** your additions via a Pull Request or GitHub Issue on this repository.
    
Your contributions make the card more visually helpful!

If you have added custom carrier logos that you think would benefit other users, feel free to contribute them to the repository! Submit a pull request with your additions to the  `carrier_logos.json`  file. This helps improve the card for everyone.




