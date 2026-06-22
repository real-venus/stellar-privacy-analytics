import { Router, Request, Response } from "express";
import { asyncHandler } from "../middleware/errorHandler";

const router = Router();

router.post(
  "/register",
  asyncHandler(async (_req: Request, res: Response) => {
    res.status(201).json({
      message: "User registered successfully",
      userId: "temp-user-id",
    });
  })
);

router.post(
  "/login",
  asyncHandler(async (_req: Request, res: Response) => {
    res.json({
      token: "temp-jwt-token",
      user: { id: "temp-user-id", email: "user@example.com" },
    });
  })
);

router.post(
  "/logout",
  asyncHandler(async (_req: Request, res: Response) => {
    res.json({ message: "Logged out successfully" });
  })
);

export { router as authRoutes };
