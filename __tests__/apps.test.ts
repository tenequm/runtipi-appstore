import { expect, test, describe } from "bun:test";
import { appInfoSchema, dynamicComposeSchemaYaml } from "@runtipi/common/schemas";
import { type } from "arktype";
import { parse as parseYaml } from "yaml";
import fs from "node:fs";
import path from "node:path";

const getApps = (): string[] => {
  const appsDir = path.join(process.cwd(), "apps");
  return fs
    .readdirSync(appsDir)
    .filter((app) => fs.statSync(path.join(appsDir, app)).isDirectory());
};

const readApp = (app: string, file: string): string | null => {
  try {
    return fs.readFileSync(path.join(process.cwd(), "apps", app, file), "utf-8");
  } catch {
    return null;
  }
};

const apps = getApps();

describe("each app has the required files", () => {
  for (const app of apps) {
    for (const file of ["config.json", "docker-compose.yml", "metadata/logo.jpg", "metadata/description.md"]) {
      test(`${app} should have ${file}`, () => {
        expect(readApp(app, file)).not.toBeNull();
      });
    }

    test(`${app} should not keep a legacy docker-compose.json`, () => {
      expect(readApp(app, "docker-compose.json")).toBeNull();
    });
  }
});

describe("each app has a valid config.json", () => {
  for (const app of apps) {
    test(`${app} config.json is valid`, () => {
      const parsed = appInfoSchema.omit("urn")(JSON.parse(readApp(app, "config.json") || "{}"));
      if (parsed instanceof type.errors) console.error(`config.json (${app}):`, parsed.summary);
      expect(parsed instanceof type.errors).toBe(false);
    });
  }
});

describe("each app has a valid docker-compose.yml", () => {
  for (const app of apps) {
    test(`${app} docker-compose.yml is valid`, () => {
      const doc = parseYaml(readApp(app, "docker-compose.yml") || "") as Record<string, any>;

      // Modern format requires top-level x-runtipi.schema_version === 2
      expect(doc?.["x-runtipi"]?.schema_version).toBe(2);

      // Validate the services structure with the official YAML schema. The top-level
      // x-runtipi key is stripped first: the exported schema models it as { overrides }
      // and would otherwise reject the (valid, docs-sanctioned) schema_version-only form.
      const { ["x-runtipi"]: _topLevel, ...services } = doc;
      const parsed = dynamicComposeSchemaYaml(services);
      if (parsed instanceof type.errors) console.error(`docker-compose.yml (${app}):`, parsed.summary);
      expect(parsed instanceof type.errors).toBe(false);

      // Exactly one main service, and it declares an internal_port for Traefik routing.
      const mains = Object.values((doc.services ?? {}) as Record<string, any>).filter(
        (s) => s?.["x-runtipi"]?.is_main,
      );
      expect(mains.length).toBe(1);
      expect(mains[0]["x-runtipi"].internal_port).toBeDefined();
    });
  }
});

describe("docker images are valid and pinned", () => {
  const imageRegex = /^([a-z0-9.-]+(\.[a-z]{2,})?\/)?[a-z0-9._-]+(\/[a-z0-9._-]+)*:[a-zA-Z0-9.v_-]+$/;

  for (const app of apps) {
    test(`${app} images are pinned (no :latest)`, () => {
      const doc = parseYaml(readApp(app, "docker-compose.yml") || "") as Record<string, any>;
      for (const service of Object.values((doc.services ?? {}) as Record<string, any>)) {
        expect(service.image).toMatch(imageRegex);
        expect(service.image).not.toMatch(/:latest$/);
      }
    });
  }
});

describe("config.json has valid timestamps", () => {
  for (const app of apps) {
    const cfg = JSON.parse(readApp(app, "config.json") || "{}");
    test(`${app} created_at`, () => expect(cfg.created_at).toBeGreaterThan(0));
    test(`${app} updated_at`, () => expect(cfg.updated_at).toBeGreaterThan(0));
  }
});
