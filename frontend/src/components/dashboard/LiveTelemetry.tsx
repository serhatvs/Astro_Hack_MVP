import { useEffect, useState } from "react";

const LiveTelemetry = () => {
  const [temp, setTemp] = useState(-64.2);
  const [pressure, setPressure] = useState(101.3);
  const [radiation, setRadiation] = useState("Nominal");

  useEffect(() => {
    const interval = setInterval(() => {
      setTemp(prev => +(prev + (Math.random() - 0.5) * 0.8).toFixed(1));
      setPressure(prev => +(prev + (Math.random() - 0.5) * 0.3).toFixed(1));
      setRadiation(Math.random() > 0.05 ? "Nominal" : "Elevated");
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-panel p-3 space-y-2">
      <h3 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Live Telemetry</h3>
      <div className="grid grid-cols-3 gap-2">
        <TelemetryItem label="Ext. Temp" value={`${temp}°C`} />
        <TelemetryItem label="Rad Shield" value={radiation} alert={radiation !== "Nominal"} />
        <TelemetryItem label="Hab. Pressure" value={`${pressure} kPa`} />
      </div>
    </div>
  );
};

const TelemetryItem = ({ label, value, alert = false }: { label: string; value: string; alert?: boolean }) => (
  <div className="text-center">
    <p className="text-[9px] font-mono uppercase text-muted-foreground tracking-wider">{label}</p>
    <p className={`text-sm font-mono font-bold ${alert ? 'text-neon-orange' : 'neon-text-cyan'}`}>{value}</p>
  </div>
);

export default LiveTelemetry;
