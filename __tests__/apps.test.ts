import { expect, test, describe } from "bun:test";
import { parseComposeJson } from '@runtipi/common/schemas'
import fs from 'node:fs'
import path from 'node:path'

interface AppConfig {
  id: string;
  name: string;
  description: string;
  version: string;
  tipi_version: number;
  short_desc: string;
  author: string;
  source: string;
  available: boolean;
  port?: number;
  categories: string[];
  supported_architectures: string[];
  dynamic_config: boolean;
  created_at: number;
  updated_at: number;
}

const getApps = async () => {
  const appsDir = await fs.promises.readdir(path.join(process.cwd(), 'apps'))

  const appDirs = appsDir.filter((app) => {
    const stat = fs.statSync(path.join(process.cwd(), 'apps', app))
    return stat.isDirectory()
  })

  return appDirs
};

const getFile = async (app: string, file: string) => {
  const filePath = path.join(process.cwd(), 'apps', app, file)
  try {
    const file = await fs.promises.readFile(filePath, 'utf-8')
    return file
  } catch (err) {
    return null
  }
}

const getAppConfigs = (): AppConfig[] => {
  const apps: AppConfig[] = [];
  const appsDir = fs.readdirSync('./apps');

  for (const app of appsDir) {
    const configPath = `./apps/${app}/config.json`;

    if (fs.existsSync(configPath)) {
      const configFile = fs.readFileSync(configPath).toString();

      try {
        const config: AppConfig = JSON.parse(configFile);
        if (config.available) {
          apps.push(config);
        }
      } catch (_) {
        console.error("Error parsing config file", app);
      }
    }
  }

  return apps;
};

describe("each app should have the required files", async () => {
  const apps = await getApps()

  for (const app of apps) {
    const files = ['config.json', 'docker-compose.json', 'metadata/logo.jpg', 'metadata/description.md']

    for (const file of files) {
      test(`app ${app} should have ${file}`, async () => {
        const fileContent = await getFile(app, file)
        expect(fileContent).not.toBeNull()
      })
    }
  }
})

describe("each app should have a valid config.json", async () => {
  const apps = getAppConfigs()

  for (const app of apps) {
    test(`app ${app.id} should have required fields`, () => {
      expect(app.id).toBeDefined();
      expect(app.name).toBeDefined();
      expect(app.description).toBeDefined();
      expect(app.short_desc).toBeDefined();
      expect(app.author).toBeDefined();
      expect(app.source).toBeDefined();
      expect(app.version).toBeDefined();
      expect(app.tipi_version).toBeDefined();
      expect(app.tipi_version).toBeGreaterThan(0);
      expect(app.categories).toBeInstanceOf(Array);
      expect(app.supported_architectures).toBeInstanceOf(Array);
    })
  }
})

describe("each app should have a valid docker-compose.json", async () => {
  const apps = getAppConfigs()

  for (const app of apps) {
    test(`app ${app.id} should have a valid docker-compose.json`, () => {
      const dockerComposeFile = fs.readFileSync(`./apps/${app.id}/docker-compose.json`).toString();
      const composeJson = JSON.parse(dockerComposeFile);

      try {
        const res = parseComposeJson(composeJson);
        expect(res).toBeDefined();
      } catch (err) {
        console.error(`Error parsing docker-compose.json for app ${app.id}:`, err);
        expect(err).toBeUndefined();
      }
    })
  }
});

describe("Docker image format validation", async () => {
  const apps = await getApps()

  for (const app of apps) {
    test(`app ${app} should have correct Docker image format`, async () => {
      const fileContent = await getFile(app, 'docker-compose.json')
      const dockerCompose = JSON.parse(fileContent || '{}')

      if (dockerCompose.services) {
        for (const service of dockerCompose.services) {
          // Basic format check: owner/repo:tag or registry/owner/repo:tag
          const imageRegex = /^([a-z0-9.-]+(\.[a-z]{2,})?\/)?[a-z0-9._-]+\/[a-z0-9._-]+:[a-z0-9.v_-]+$/i
          expect(service.image).toMatch(imageRegex)
        }
      }
    })
  }
});

describe("All apps should have valid timestamps", () => {
  const apps = getAppConfigs();

  for (const app of apps) {
    test(`${app.id} should have valid created_at`, () => {
      expect(app.created_at).toBeDefined();
      expect(app.created_at).toBeGreaterThan(0);
    });

    test(`${app.id} should have valid updated_at`, () => {
      expect(app.updated_at).toBeDefined();
      expect(app.updated_at).toBeGreaterThan(0);
    });
  }
});
