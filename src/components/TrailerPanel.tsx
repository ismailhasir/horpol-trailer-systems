import { setLengths, sockets, trailerTypes } from "../config/catalog";
import { configStore, useConfiguration } from "../state/store";
import { OptionGroup } from "./OptionGroup";

export function TrailerPanel() {
  const config = useConfiguration();
  return (
    <>
      <section className="section">
        <h2>Dorse</h2>
        <OptionGroup
          label="Dorse tipi"
          options={trailerTypes}
          value={config.trailerTypeId}
          onChange={(id) => configStore.set((c) => ({ ...c, trailerTypeId: id }))}
        />
      </section>
      <section className="section">
        <h2>Set özellikleri</h2>
        <OptionGroup
          label="Soket tipi"
          options={sockets}
          value={config.socketId}
          onChange={(id) => configStore.set((c) => ({ ...c, socketId: id }))}
        />
        <OptionGroup
          label="Set uzunluğu"
          options={setLengths}
          value={config.setLengthId}
          onChange={(id) => configStore.set((c) => ({ ...c, setLengthId: id }))}
        />
      </section>
    </>
  );
}
