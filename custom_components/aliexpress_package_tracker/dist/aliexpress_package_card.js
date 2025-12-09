const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace")
);
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

class AliExpressPackageCard extends LitElement {
  static properties = {
    hass: {},
    config: {},
    carrierLogos: { type: Object },
    translations: { state: true }, // Holds the loaded translations for the selected language
    enTranslations: { state: true }, // Holds the loaded English translations (fallback)
    _translationsLoading: { state: true }, // Track loading state
  };
  static rtlLanguages = ["ar", "he"]; // Add other RTL codes if needed
  constructor() {
    super();
    this.carrierLogos = {};
    this.translations = null;
    this.enTranslations = null;
    this._translationsLoading = false;
    this._basePath = new URL(".", import.meta.url).pathname;
    console.log("Base path:", this._basePath);
    this.loadCarrierLogos();
  }

  // --- Load Carrier Logos (Unchanged) ---
  async loadCarrierLogos() {
    try {
      const response = await fetch(`${this._basePath}carrier_logos.json`);
      if (response.ok) {
        this.carrierLogos = await response.json();
      } else {
        console.error(
          "AliExpress Card: Failed to load carrier logos JSON:",
          response.statusText,
          `Path: ${this._basePath}carrier_logos.json`
        );
      }
    } catch (error) {
      console.error(
        "AliExpress Card: Error loading carrier logos JSON:",
        error
      );
    }
  }

  // --- Load Translations based on Config ---
  async loadTranslations() {
    if (this._translationsLoading) return; // Prevent simultaneous loads

    this._translationsLoading = true;
    const lang = this.config?.language || "en";
    let loadedLangData = null;
    let loadedEnData = null;

    // Always try to load English first as fallback
    try {
      const enResponse = await fetch(`${this._basePath}translations/en.json`);
      if (enResponse.ok) {
        loadedEnData = await enResponse.json();
        console.debug("AliExpress Card: Loaded en.json fallback.");
      } else {
        console.error(
          "AliExpress Card: Failed to load mandatory en.json:",
          enResponse.statusText
        );
      }
    } catch (error) {
      console.error("AliExpress Card: Error loading en.json:", error);
    }
    this.enTranslations = loadedEnData; // Store loaded English data (or null if failed)

    // Load selected language if it's not English
    if (lang !== "en") {
      try {
        const langResponse = await fetch(
          `${this._basePath}translations/${lang}.json`
        );
        if (langResponse.ok) {
          loadedLangData = await langResponse.json();
          console.debug(`AliExpress Card: Loaded ${lang}.json.`);
        } else {
          console.warn(
            `AliExpress Card: Failed to load ${lang}.json (${langResponse.statusText}), using English fallback.`
          );
        }
      } catch (error) {
        console.error(`AliExpress Card: Error loading ${lang}.json:`, error);
      }
    } else {
      // If lang is 'en', use the already loaded English data
      loadedLangData = loadedEnData;
    }

    this.translations = loadedLangData; // Store loaded language data (or null if failed)
    this._translationsLoading = false;
    this.requestUpdate(); // Trigger re-render with loaded translations
  }

  // --- Get Translation String ---
  _getTranslation(key) {
    const keyParts = key.split(".");
    let currentLevel = this.translations; // Try selected language first

    // Traverse translations object
    for (const part of keyParts) {
      if (
        currentLevel &&
        typeof currentLevel === "object" &&
        part in currentLevel
      ) {
        currentLevel = currentLevel[part];
      } else {
        currentLevel = null; // Key not found in selected language path
        break;
      }
    }

    // If found and is a string, return it
    if (currentLevel !== null && typeof currentLevel === "string") {
      return currentLevel;
    }

    // --- Fallback to English ---
    currentLevel = this.enTranslations; // Reset to English root
    if (!currentLevel) {
      // English failed to load entirely
      console.warn(
        `AliExpress Card: Translation key '${key}' lookup failed, English fallback unavailable.`
      );
      return keyParts[keyParts.length - 1]; // Return last part of the key
    }

    for (const part of keyParts) {
      if (
        currentLevel &&
        typeof currentLevel === "object" &&
        part in currentLevel
      ) {
        currentLevel = currentLevel[part];
      } else {
        console.warn(
          `AliExpress Card: Translation key '${key}' not found in selected language or English fallback.`
        );
        return keyParts[keyParts.length - 1]; // Return last part of the key
      }
    }

    // Return English fallback if it's a string
    return typeof currentLevel === "string"
      ? currentLevel
      : keyParts[keyParts.length - 1];
  }

  // --- setConfig: Store config and trigger translation load ---
  setConfig(config) {
    if (JSON.stringify(config) !== JSON.stringify(this.config)) {
      this.config = config;
      // Reset translations and load new ones if language might have changed
      this.translations = null;
      // Keep enTranslations loaded if possible
      // this.enTranslations = null; // Optionally force reload of English too
      this.loadTranslations();
    }
  }

  // --- Ensure translations are loaded when element connects or config updates ---
  connectedCallback() {
    super.connectedCallback();
    if (!this.translations && !this._translationsLoading) {
      this.loadTranslations();
    }
  }

  // --- Styles (Keep existing) ---
  static styles = css`
    .card {
      padding: 16px;
      background-color: var(--card-background-color, #f9f9f9);
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      direction: ltr;
      text-align: left;
    }
    .package {
      margin-bottom: 16px;
      padding: 10px;
      border: 1px solid var(--divider-color, #ccc);
      border-radius: 8px;
      background-color: var(--primary-background-color, #fff);
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 1.4em;
      font-weight: bold;
      margin-bottom: 16px;
      color: var(--primary-text-color);
      user-select: text;
    }
    .actions {
      display: flex;
      gap: 8px;
      margin-left: auto;
    }
    .attribute {
      display: flex;
      align-items: center;
      margin: 4px 0;
      color: var(--primary-text-color);
      user-select: text;
    }
    .attribute span:first-child {
      margin-right: 8px;
      min-width: 20px;
      text-align: center;
      margin-inline-end: 8px;
    }
    .attribute b {
      margin-right: 4px;
    }
    .link {
      color: var(--link-color, blue);
      text-decoration: underline;
      cursor: pointer;
      user-select: text;
      word-break: break-all;
    }
    ha-icon-button {
      --mdc-icon-button-size: 32px;
      --mdc-icon-size: 20px;
    }
    .add-tracking {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
    }
    .add-tracking input {
      flex: 1;
      padding: 8px;
      border: none;
      border-bottom: 1px solid var(--divider-color, #ccc);
      outline: none;
      background: transparent;
      color: var(--primary-text-color);
      user-select: text;
    }
    .add-tracking button {
      padding: 8px;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 1.2em;
      color: var(--primary-text-color);
    }
    .actions button {
      border: none;
      background: none;
      cursor: pointer;
      font-size: 1.2em;
      color: var(--primary-text-color);
    }
    .carrier-logo {
      height: 48px;
      max-width: 100px;
      object-fit: contain;
      margin-right: 8px;
    }
    .title-text {
      flex: 1;
      word-break: break-word;
    }
    .card.rtl {
      direction: rtl;
      text-align: right;
    }

    .rtl .actions {
      margin-left: 0; /* Reset LTR push */
      margin-right: auto; /* Push actions to the end in RTL */
    }
  `;

  // --- Attribute Order & Icons (Unchanged) ---
  static attributeOrder = [
    "status",
    "last_update_status",
    "last_update_time",
    "progressStatus",
    "daysNumber",
    "carrier",
    "originCountry",
    "destCountry",
    "orignal_track_id",
    "order_number",
    "carrier_url",
    "order_url",
  ];
  static attributeIcons = {
    order_number: "🔢",
    status: "📦",
    last_update_time: "⏰",
    last_update_status: "🕒",
    progressStatus: "📈",
    carrier: "🚚",
    carrier_url: "🔗",
    daysNumber: "📅",
    orignal_track_id: "🔖",
    order_url: "🔗",
    originCountry: "🌍",
    destCountry: "🌎",
  };

  // --- Get Entities (Unchanged) ---
  getAliExpressEntities() {
    /* ... */
    if (!this.hass || !this.hass.states) return [];
    return Object.keys(this.hass.states).filter(
      (entity_id) =>
        entity_id.startsWith("sensor.") &&
        this.hass.states[entity_id]?.attributes?.attribution?.includes(
          "Cainiao API"
        )
    );
  }

  // --- Actions (Use _getTranslation for titles/prompts) ---
  handleRemove(entity_id) {
    this.hass.callService("aliexpress_package_tracker", "remove_tracking", {
      entity_id: [entity_id],
    });
  }

  handleEdit(entity_id, title) {
    const promptTitle =
      this._getTranslation("common.edit_title") || "Edit Title";
    const newTitle = prompt(promptTitle + ":", title || "");
    if (newTitle !== null && newTitle !== (title || "")) {
      this.hass.callService("aliexpress_package_tracker", "edit_title", {
        entity_id: [entity_id],
        new_title: newTitle,
      });
    }
  }

  handleAddTracking() {
    const trackingInput = this.shadowRoot.getElementById("trackingInput");
    const trackingNumber = trackingInput.value.trim();
    if (trackingNumber) {
      const titlePrompt =
        this._getTranslation("common.enter_title_optional") ||
        "Enter title (optional):";
      const newTitle = prompt(titlePrompt, "");
      this.hass.callService("aliexpress_package_tracker", "add_tracking", {
        tracking_number: trackingNumber,
        title: newTitle || "",
      });
      trackingInput.value = "";
    } else {
      alert(
        this._getTranslation("common.enter_tracking_alert") ||
          "Please enter a tracking number."
      );
    }
  }

  formatTime(timeString) {
    const notAvailable = this._getTranslation("common.not_available") || "N/A";
    if (!timeString) return notAvailable;
    try {
      const date = new Date(timeString);
      if (isNaN(date.getTime())) {
        return timeString;
      }
      return date.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      console.error("Error formatting time:", timeString, e);
      return timeString;
    }
  }

  getAttributeLabel(key) {
    const translationKey = `attribute.${key}`;
    const translated = this._getTranslation(translationKey);
    // Basic fallback if translation failed
    return translated !== translationKey
      ? translated
      : key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  getTranslatedStatusValue(statusKey) {
    const upperKey = String(statusKey).toUpperCase();
    const translationKey = `status_value.${upperKey}`;
    const translated = this._getTranslation(translationKey);
    // Fallback to original key if translation failed or is same as key
    return translated !== translationKey && translated !== upperKey
      ? translated
      : statusKey;
  }

  render() {
    if (
      !this.hass ||
      (!this.translations && !this.enTranslations && !this._translationsLoading)
    ) {
      // Show loading or basic state if translations aren't ready
      return html`<ha-card
        ><div style="padding:16px;">Loading translations...</div></ha-card
      >`;
    }
    if (
      !this.translations &&
      !this.enTranslations &&
      this._translationsLoading
    ) {
      return html`<ha-card
        ><div style="padding:16px;">Loading translations...</div></ha-card
      >`;
    }
    if (!this.enTranslations) {
      // Critical fallback missing
      return html`<ha-card
        ><div style="padding:16px; color: red;">
          Error: Could not load base English translations (en.json). Card cannot
          function.
        </div></ha-card
      >`;
    }
    const currentLang = this.config?.language || "en";
    const isRTL = AliExpressPackageCard.rtlLanguages.includes(currentLang);
    const cardClassString = `card ${isRTL ? "rtl" : ""}`;

    const entities = this.getAliExpressEntities();
    const showAddTracking = !this.config?.hide_add_tracking;
    const cardTitle =
      this.config?.title ||
      this._getTranslation("common.default_title") ||
      "AliExpress Packages"; // Final fallback

    return html`
      <ha-card class="${cardClassString}">
        <div class="header">${cardTitle}</div>
        ${showAddTracking
          ? html`
              <div class="add-tracking">
                <input
                  id="trackingInput"
                  type="text"
                  placeholder="${this._getTranslation(
                    "common.enter_tracking_number"
                  ) || "Enter tracking number"}"
                  @keyup=${(e) => e.key === "Enter" && this.handleAddTracking()}
                />
                <button
                  @click="${this.handleAddTracking}"
                  title="${this._getTranslation("common.add_tracking") ||
                  "Add Tracking"}"
                >
                  ➕
                </button>
              </div>
            `
          : ""}
        ${entities.length === 0
          ? html`<div>
              ${this._getTranslation("common.no_packages") ||
              "No tracked packages found."}
            </div>`
          : entities.map((entity_id) => {
              const entity = this.hass.states[entity_id];
              if (!entity || !entity.attributes) {
                return html`<div>
                  ${this._getTranslation("common.error_loading") ||
                  "Error loading entity:"}
                  ${entity_id}
                </div>`;
              }

              const excludedAttributes = [
                "title",
                "icon",
                "attribution",
                "friendly_name",
                "status_english",
                ...(this.config?.exclude_attributes || []),
              ];

              const filteredAttributes = Object.entries(entity.attributes)
                .filter(
                  ([key, value]) =>
                    value !== null &&
                    value !== "" &&
                    !excludedAttributes.includes(key)
                )
                .sort(([keyA], [keyB]) => {
                  /* ... sorting ... */
                  const indexA =
                    AliExpressPackageCard.attributeOrder.indexOf(keyA);
                  const indexB =
                    AliExpressPackageCard.attributeOrder.indexOf(keyB);
                  if (indexA !== -1 && indexB !== -1) return indexA - indexB;
                  if (indexA !== -1) return -1;
                  if (indexB !== -1) return 1;
                  return keyA.localeCompare(keyB);
                });

              const carrier = entity.attributes["carrier"];
              const carrierUrl = entity.attributes["carrier_url"];
              const carrierLogo =
                /* ... logo logic ... */
                carrier && this.carrierLogos[carrier]
                  ? html`<img
                      src="${this.carrierLogos[carrier]}"
                      alt="${carrier} logo"
                      class="carrier-logo"
                    />`
                  : carrierUrl
                  ? html`<img
                      src="https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=${encodeURIComponent(
                        carrierUrl
                      )}&size=64"
                      alt="${carrier || "Carrier"} logo"
                      class="carrier-logo"
                      @error=${(e) => (e.target.style.display = "none")}
                    />`
                  : null;

              const title =
                entity.attributes.title ||
                entity.attributes.friendly_name ||
                entity_id;

              return html`
                <div class="package">
                  <div class="header">
                    ${carrierLogo || ""}
                    <span class="title-text">${title}</span>
                    <div class="actions">
                      <button
                        title="${this._getTranslation("common.edit_title") ||
                        "Edit Title"}"
                        @click=${() => this.handleEdit(entity.entity_id, title)}
                      >
                        ✏️
                      </button>
                      <button
                        title="${this._getTranslation(
                          "common.remove_tracking"
                        ) || "Remove Tracking"}"
                        @click="${() => this.handleRemove(entity_id)}"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                  ${filteredAttributes.map(([key, value]) => {
                    let icon =
                      AliExpressPackageCard.attributeIcons[key] || "ℹ️";
                    let displayValue;
                    if (key === "progressStatus") {
                      icon = value === "NORMAL" ? "🟢" : "🔴";
                      displayValue = this.getTranslatedStatusValue(value);
                    } else if (key.includes("time")) {
                      displayValue = this.formatTime(value);
                    } else {
                      displayValue = String(value);
                    }
                    const isLink =
                      typeof value === "string" &&
                      value.toLowerCase().startsWith("http");

                    return html`
                      <div class="attribute">
                        <span>${icon}</span>
                        <b>${this.getAttributeLabel(key)}:</b>
                        ${isLink
                          ? html`<a
                              href="${value}"
                              target="_blank"
                              class="link"
                              rel="noopener noreferrer"
                              >${value}</a
                            >`
                          : html`<span>${displayValue}</span>`}
                      </div>
                    `;
                  })}
                </div>
              `;
            })}
      </ha-card>
    `;
  }

  static getConfigElement() {
    return document.createElement("aliexpress-package-card-editor");
  }

  static getStubConfig() {
    // Default language is implicitly 'en' (or handled by fallback)
    return { exclude_attributes: [], hide_add_tracking: false };
  }
}

customElements.define("aliexpress-package-card", AliExpressPackageCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "aliexpress-package-card",
  name: "AliExpress Package Card",
  preview: true,
  description: "Displays AliExpress packages with file-based translations.",
});

class AliExpressPackageCardEditor extends LitElement {
  static properties = {
    hass: {},
    _config: { state: true },
    _availableLanguages: { state: true }, // Store language list from index.json
    _loadingLanguages: { state: true }, // Track loading state
  };

  constructor() {
    super();
    this._availableLanguages = [];
    this._loadingLanguages = false;

    this._basePath = new URL(".", import.meta.url).pathname;
  }

  // --- Load available languages from index.json ---
  async _loadLanguageIndex() {
    if (this._loadingLanguages || this._availableLanguages.length > 0) return; // Don't reload if already loaded or loading

    this._loadingLanguages = true;
    try {
      console.log(`${this._basePath}translations/index.json`);
      const response = await fetch(`${this._basePath}translations/index.json`);
      if (response.ok) {
        const languages = await response.json();
        // Ensure it's an array and has the expected structure
        if (
          Array.isArray(languages) &&
          languages.every((l) => l.code && l.name)
        ) {
          // Add a "Default" option conceptually (maps to 'en' or undefined)
          // We handle this in the selector logic instead of modifying the array
          this._availableLanguages = languages;
          console.debug("AliExpress Card Editor: Loaded languages", languages);
        } else {
          console.error(
            "AliExpress Card Editor: Invalid format in translations/index.json"
          );
          this._availableLanguages = [
            { code: "en", name: "English (Default Only)" },
          ]; // Provide basic fallback
        }
      } else {
        console.error(
          "AliExpress Card Editor: Failed to load translations/index.json:",
          response.statusText
        );
        this._availableLanguages = [
          { code: "en", name: "English (Index Load Failed)" },
        ]; // Provide basic fallback
      }
    } catch (error) {
      console.error(
        "AliExpress Card Editor: Error loading translations/index.json:",
        error
      );
      this._availableLanguages = [
        { code: "en", name: "English (Index Load Error)" },
      ]; // Provide basic fallback
    } finally {
      this._loadingLanguages = false;
      this.requestUpdate(); // Update the editor view with loaded languages
    }
  }

  setConfig(config) {
    this._config = config;
    // Trigger loading language list when config is set
    this._loadLanguageIndex();
  }

  connectedCallback() {
    super.connectedCallback();
    // Also try loading if component connects and languages aren't loaded
    if (this._availableLanguages.length === 0) {
      this._loadLanguageIndex();
    }
  }

  _valueChanged(ev) {
    if (!this._config) return;

    const newConfig = { ...this._config, ...ev.detail.value }; // Merge changes

    // Ensure exclude_attributes is always an array
    if (newConfig.exclude_attributes === undefined) {
      newConfig.exclude_attributes = [];
    } else if (!Array.isArray(newConfig.exclude_attributes)) {
      newConfig.exclude_attributes = [newConfig.exclude_attributes];
    }

    // Handle empty title
    if (newConfig.title === "") {
      delete newConfig.title;
    }
    // Handle language selection - if 'en' (our default value for the default option), remove the key
    if (newConfig.language === "en") {
      delete newConfig.language;
    }

    if (JSON.stringify(newConfig) !== JSON.stringify(this._config)) {
      this._config = newConfig;
      const event = new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      });
      this.dispatchEvent(event);
    }
  }

  render() {
    if (!this.hass || !this._config || this._loadingLanguages) {
      // Show loading state for languages if needed
      return html`<div style="padding:16px;">Loading editor...</div>`;
    }
    if (this._availableLanguages.length === 0 && !this._loadingLanguages) {
      // Attempt to load languages if failed previously maybe? Or just show error.
      this._loadLanguageIndex(); // Try again
      return html`<div style="padding:16px;">Loading language options...</div>`;
    }

    const allAttributes = AliExpressPackageCard.attributeOrder.concat(
      Object.keys(AliExpressPackageCard.attributeIcons).filter(
        (attr) => !AliExpressPackageCard.attributeOrder.includes(attr)
      )
    );

    // Editor labels - keep simple or fetch from index.json if defined there? Let's keep simple.
    const titleLabel = "Card Title (Optional)";
    const langLabel = "Card Language";
    const hideAddLabel = "Hide 'Add Tracking' Section";
    const excludeLabel = "Exclude Attributes (Select to hide)";

    // Prepare language options for the dropdown
    // Ensure 'en' is the first option and represents the default
    const languageOptions = this._availableLanguages
      .sort((a, b) => {
        if (a.code === "en") return -1; // 'en' comes first
        if (b.code === "en") return 1;
        return a.name.localeCompare(b.name); // Sort others alphabetically by name
      })
      .map((lang) => ({
        value: lang.code,
        label: lang.name,
      }));

    const schema = [
      { name: "title", selector: { text: {} }, label: titleLabel },
      {
        name: "language",
        selector: {
          select: {
            options: languageOptions,
            mode: "dropdown", // Use dropdown mode
          },
        },
        label: langLabel,
      },
      {
        name: "hide_add_tracking",
        selector: { boolean: {} },
        label: hideAddLabel,
      },
      {
        name: "exclude_attributes",
        selector: {
          select: {
            multiple: true,
            options: allAttributes.map((attr) => ({
              value: attr,
              // Use a simple generated label for attributes in editor
              label: attr
                .replace(/_/g, " ")
                .replace(/\b\w/g, (c) => c.toUpperCase()),
            })),
            custom_value: false,
            sort: false,
          },
        },
        label: excludeLabel,
      },
    ];

    // Set data for the form
    const data = {
      title: this._config.title ?? "",
      // Use 'en' as the value if language is not set (maps to the 'English (Default)' option)
      language: this._config.language ?? "en",
      hide_add_tracking: this._config.hide_add_tracking ?? false,
      exclude_attributes: this._config.exclude_attributes ?? [],
    };

    return html`
      <ha-form
        .hass=${this.hass}
        .data=${data}
        .schema=${schema}
        .computeLabel=${(schema) => schema.label || schema.name}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `;
  }

  static styles = css`
    ha-form {
      display: block;
      padding: 16px;
    }
    ha-textfield {
      width: 100%;
    }
    /* Ensure dropdown is visible */
    ha-select {
      width: 100%;
    }
  `;
}

customElements.define(
  "aliexpress-package-card-editor",
  AliExpressPackageCardEditor
);
