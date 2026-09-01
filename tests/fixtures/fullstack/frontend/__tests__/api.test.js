import { greet } from "../../src/utils";
test("greet from JS", () => {
  expect(greet("js")).toBe("hello, js");
});
