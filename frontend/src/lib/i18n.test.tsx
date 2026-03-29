import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import LanguageToggle from "@/components/LanguageToggle";
import { I18nProvider, getTranslation, useI18n } from "@/lib/i18n";

const TranslationProbe = () => {
  const { t } = useI18n();
  return <span>{t("generate_plan")}</span>;
};

describe("i18n", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("defaults to English and switches to Turkish", () => {
    render(
      <I18nProvider>
        <LanguageToggle />
        <TranslationProbe />
      </I18nProvider>,
    );

    expect(screen.getByText("Generate Plan")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "TR" }));

    expect(screen.getByText(getTranslation("tr", "generate_plan"))).toBeInTheDocument();
    expect(window.localStorage.getItem("astro-hack:ui-language")).toBe("tr");
  });

  it("restores persisted language and falls back safely for missing keys", () => {
    window.localStorage.setItem("astro-hack:ui-language", "tr");

    render(
      <I18nProvider>
        <TranslationProbe />
      </I18nProvider>,
    );

    expect(screen.getByText(getTranslation("tr", "generate_plan"))).toBeInTheDocument();
    expect(getTranslation("tr", "__missing_key__")).toBe("__missing_key__");
  });
});
