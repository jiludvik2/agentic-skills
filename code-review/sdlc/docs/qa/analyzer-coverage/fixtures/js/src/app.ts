// depcruiser __mocks__ coupling: a production module reaching into test-scaffolding.
// The planted smell: src/app.ts (non-mock source) depends on __mocks__/service.ts.
import { svc } from "../__mocks__/service";

export const useApp = (): number => svc();
