import { Request } from "express";
import { TransformationRule } from "../PrivacyApiGateway";
import {
  RequestTransformer,
  RequestWithTransformations,
} from "../RequestTransformer";

jest.mock("../../utils/logger");

describe("RequestTransformer", () => {
  describe("applyRequestTransformations", () => {
    it("stores transformed request data without mutating Express request objects", async () => {
      const transformer = new RequestTransformer();
      const req = {
        body: {
          email: "person@example.com",
          profile: {
            phone: "555-0100",
          },
        },
        query: {
          token: "secret-token",
        },
        params: {
          userId: "user-123",
        },
        headers: {
          "x-jurisdiction": "US",
          "x-purpose": "analytics",
        },
      } as unknown as RequestWithTransformations;

      const cachedBody = req.body;
      const cachedQuery = req.query;
      const cachedParams = req.params;

      const rules: TransformationRule[] = [
        {
          type: "mask",
          field: "req.body.email",
          parameters: {
            type: "full",
            maskChar: "#",
          },
        },
        {
          type: "mask",
          field: "request.body.profile.phone",
          parameters: {
            type: "full",
            maskChar: "*",
          },
        },
        {
          type: "mask",
          field: "request.query.token",
          parameters: {
            type: "full",
            maskChar: "x",
          },
        },
        {
          type: "mask",
          field: "request.params.userId",
          parameters: {
            type: "full",
            maskChar: "_",
          },
        },
      ];

      const result = await transformer.applyRequestTransformations(
        req as Request,
        rules,
      );

      expect(result).toMatchObject({
        success: true,
        transformed: true,
      });

      expect(req.body).toBe(cachedBody);
      expect(req.query).toBe(cachedQuery);
      expect(req.params).toBe(cachedParams);

      expect(cachedBody).toEqual({
        email: "person@example.com",
        profile: {
          phone: "555-0100",
        },
      });
      expect(cachedQuery).toEqual({
        token: "secret-token",
      });
      expect(cachedParams).toEqual({
        userId: "user-123",
      });

      expect(req.transformedRequest).toBeDefined();
      expect(req.transformedRequest!.body).not.toBe(cachedBody);
      expect(req.transformedRequest!.query).not.toBe(cachedQuery);
      expect(req.transformedRequest!.params).not.toBe(cachedParams);
      expect(req.transformedRequest!.body).toEqual({
        email: "##################",
        profile: {
          phone: "********",
        },
      });
      expect(req.transformedRequest!.query).toEqual({
        token: "xxxxxxxxxxxx",
      });
      expect(req.transformedRequest!.params).toEqual({
        userId: "________",
      });
      expect(result.data).toBe(req.transformedRequest);
    });
  });
});
