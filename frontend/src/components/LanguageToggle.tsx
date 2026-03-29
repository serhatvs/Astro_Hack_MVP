import { useI18n } from "@/lib/i18n";

const buttonClass =
  "px-2 py-1 text-[10px] font-mono uppercase tracking-wider transition-colors";

const LanguageToggle = () => {
  const { language, setLanguage, t } = useI18n();

  return (
    <div
      className="inline-flex items-center overflow-hidden rounded border border-glass-border bg-muted/20"
      aria-label={t("language_toggle")}
    >
      <button
        type="button"
        onClick={() => setLanguage("en")}
        aria-pressed={language === "en"}
        className={`${buttonClass} ${
          language === "en"
            ? "bg-neon-cyan/15 text-neon-cyan"
            : "text-muted-foreground hover:bg-muted/30"
        }`}
      >
        {t("language_en")}
      </button>
      <button
        type="button"
        onClick={() => setLanguage("tr")}
        aria-pressed={language === "tr"}
        className={`${buttonClass} ${
          language === "tr"
            ? "bg-neon-cyan/15 text-neon-cyan"
            : "text-muted-foreground hover:bg-muted/30"
        }`}
      >
        {t("language_tr")}
      </button>
    </div>
  );
};

export default LanguageToggle;
