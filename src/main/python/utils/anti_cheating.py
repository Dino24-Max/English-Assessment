"""
Anti-cheating measures for assessments
Implements IP tracking, user agent validation, and suspicious behavior detection
"""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List
import json
from datetime import datetime
from models.assessment import Assessment


class AntiCheatingService:
    """Implements anti-cheating measures"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_session_start(self, assessment_id: int, request: Request) -> Dict[str, Any]:
        """
        Record session start data for anti-cheating
        Captures IP address, user agent, and session metadata
        """
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "Unknown")

        # Get assessment
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()

        if assessment:
            # Store anti-cheating data
            assessment.ip_address = client_ip
            assessment.user_agent = user_agent

            # Initialize analytics data with session start info
            if not assessment.analytics_data:
                assessment.analytics_data = {}

            assessment.analytics_data.update({
                "session_start_time": datetime.utcnow().isoformat(),
                "initial_ip": client_ip,
                "initial_user_agent": user_agent,
                "suspicious_events": [],
                "tab_switches": 0,
                "copy_paste_attempts": 0
            })

            await self.db.commit()

        return {
            "ip_address": client_ip,
            "user_agent": user_agent,
            "recorded": True
        }

    async def validate_session(self, assessment_id: int, request: Request) -> Dict[str, Any]:
        """
        Validate session integrity
        Checks for IP changes, user agent changes, and suspicious behavior
        Returns validation result with details
        """
        # Get current request info
        current_ip = self._get_client_ip(request)
        current_user_agent = request.headers.get("user-agent", "Unknown")

        # Get assessment with stored data
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()

        if not assessment:
            return {
                "valid": False,
                "reason": "Assessment not found",
                "suspicious": True
            }

        # Check IP consistency
        ip_changed = assessment.ip_address and assessment.ip_address != current_ip

        # Check user agent consistency
        ua_changed = assessment.user_agent and assessment.user_agent != current_user_agent

        # Determine if session is suspicious
        suspicious = ip_changed or ua_changed
        warnings = []

        if ip_changed:
            warnings.append(f"IP address changed from {assessment.ip_address} to {current_ip}")

        if ua_changed:
            warnings.append("User agent (browser/device) changed during assessment")

        # Log suspicious event
        if suspicious:
            await self._log_suspicious_event(
                assessment_id,
                "session_validation_failed",
                {
                    "ip_changed": ip_changed,
                    "ua_changed": ua_changed,
                    "current_ip": current_ip,
                    "current_user_agent": current_user_agent,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        return {
            "valid": not suspicious,
            "suspicious": suspicious,
            "warnings": warnings,
            "ip_consistent": not ip_changed,
            "user_agent_consistent": not ua_changed,
            "details": {
                "stored_ip": assessment.ip_address,
                "current_ip": current_ip,
                "ip_match": not ip_changed
            }
        }

    async def record_tab_switch(self, assessment_id: int) -> Dict[str, Any]:
        """
        Record tab switching event
        Called from frontend when visibility API detects tab switch
        """
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()

        if assessment and assessment.analytics_data:
            # Increment tab switch counter
            tab_switches = assessment.analytics_data.get("tab_switches", 0) + 1
            assessment.analytics_data["tab_switches"] = tab_switches

            # Log event
            await self._log_suspicious_event(
                assessment_id,
                "tab_switch",
                {
                    "count": tab_switches,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            await self.db.commit()

            return {
                "recorded": True,
                "total_switches": tab_switches,
                "warning": tab_switches > 3  # Flag if more than 3 switches
            }

        return {"recorded": False}

    async def record_copy_paste(self, assessment_id: int, action: str) -> Dict[str, Any]:
        """
        Record copy/paste attempts
        Called from frontend when copy/paste events detected
        """
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()

        if assessment and assessment.analytics_data:
            # Increment copy/paste counter
            attempts = assessment.analytics_data.get("copy_paste_attempts", 0) + 1
            assessment.analytics_data["copy_paste_attempts"] = attempts

            # Log event
            await self._log_suspicious_event(
                assessment_id,
                f"copy_paste_{action}",
                {
                    "action": action,
                    "count": attempts,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            await self.db.commit()

            return {
                "recorded": True,
                "total_attempts": attempts,
                "warning": attempts > 5  # Flag if more than 5 attempts
            }

        return {"recorded": False}

    async def get_suspicious_score(self, assessment_id: int) -> Dict[str, Any]:
        """
        Calculate suspicious behavior score
        Returns score from 0 (clean) to 100 (highly suspicious)
        """
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()

        if not assessment or not assessment.analytics_data:
            return {"score": 0, "level": "clean"}

        analytics = assessment.analytics_data
        score = 0
        factors = []

        # IP change: +40 points
        validation = await self.validate_session(assessment_id, None)
        if not validation.get("ip_consistent", True):
            score += 40
            factors.append("IP address changed")

        # User agent change: +30 points
        if not validation.get("user_agent_consistent", True):
            score += 30
            factors.append("Browser/device changed")

        # Tab switches: +5 points per switch (max 20)
        tab_switches = analytics.get("tab_switches", 0)
        if tab_switches > 0:
            switch_penalty = min(tab_switches * 5, 20)
            score += switch_penalty
            factors.append(f"{tab_switches} tab switches")

        # Copy/paste attempts: +3 points per attempt (max 15)
        copy_paste = analytics.get("copy_paste_attempts", 0)
        if copy_paste > 0:
            paste_penalty = min(copy_paste * 3, 15)
            score += paste_penalty
            factors.append(f"{copy_paste} copy/paste attempts")

        # Suspicious events: +10 points each (max 20)
        suspicious_events = len(analytics.get("suspicious_events", []))
        if suspicious_events > 0:
            event_penalty = min(suspicious_events * 10, 20)
            score += event_penalty
            factors.append(f"{suspicious_events} suspicious events")

        # Determine level
        if score >= 70:
            level = "critical"  # Likely cheating
        elif score >= 40:
            level = "high"  # Suspicious
        elif score >= 20:
            level = "medium"  # Somewhat suspicious
        elif score > 0:
            level = "low"  # Minor concerns
        else:
            level = "clean"  # No issues

        return {
            "score": score,
            "level": level,
            "factors": factors,
            "requires_review": score >= 40
        }

    async def _log_suspicious_event(self, assessment_id: int, event_type: str,
                                   details: Dict[str, Any]) -> None:
        """Log a suspicious event to assessment analytics"""
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()

        if assessment:
            if not assessment.analytics_data:
                assessment.analytics_data = {"suspicious_events": []}

            if "suspicious_events" not in assessment.analytics_data:
                assessment.analytics_data["suspicious_events"] = []

            assessment.analytics_data["suspicious_events"].append({
                "type": event_type,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            })

            await self.db.commit()

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request
        Handles proxies and load balancers
        """
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return forwarded.split(",")[0].strip()

        # Check real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "Unknown"

    async def flag_for_review(self, assessment_id: int, reason: str) -> Dict[str, Any]:
        """
        Flag an assessment for manual review
        """
        result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()

        if assessment:
            if not assessment.analytics_data:
                assessment.analytics_data = {}

            assessment.analytics_data["flagged_for_review"] = True
            assessment.analytics_data["flag_reason"] = reason
            assessment.analytics_data["flag_timestamp"] = datetime.utcnow().isoformat()

            await self.db.commit()

            return {"flagged": True, "reason": reason}

        return {"flagged": False, "error": "Assessment not found"}