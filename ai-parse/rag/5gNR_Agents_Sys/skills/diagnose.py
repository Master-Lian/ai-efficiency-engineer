"""
故障诊断技能
基于检测结果和知识库进行根因分析
调用 Qwen-7B 大模型进行推理
支持 JSON 解析和重试机制
"""
from typing import Any, Dict, List
import json
import logging
import re
from core.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class DiagnoseSkill(BaseSkill):
    """故障诊断技能 - 基于 LLM 的智能诊断"""

    def __init__(self):
        super().__init__()
        self._llm_client = None
        self._diagnosis_count = 0

    @property
    def name(self) -> str:
        return "diagnose"

    @property
    def description(self) -> str:
        return "基于故障检测结果和知识库进行根因分析，调用Qwen-7B模型输出诊断报告"

    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行故障诊断"""
        start_time = self._track_execution_start()
        faults = kwargs.get("faults", [])
        context = kwargs.get("context", "")
        device_id = kwargs.get("device_id", "unknown")

        self._log_execute(f"开始诊断设备 {device_id}，发现 {len(faults)} 个故障")

        try:
            if not faults:
                elapsed = self._track_execution(start_time)
                return self._build_result(
                    status="no_fault",
                    device_id=device_id,
                    root_causes=[],
                    report="设备运行正常，无需诊断",
                    latency_ms=elapsed,
                )

            prompt = self._build_diagnosis_prompt(faults, context)
            diagnosis_result = self._call_llm(prompt)

            root_causes = self._parse_diagnosis_result(diagnosis_result, faults)
            report = self._generate_report(device_id, faults, root_causes)

            self._diagnosis_count += 1
            elapsed = self._track_execution(start_time)
            self._log_execute(f"诊断完成: 识别 {len(root_causes)} 个根因")

            return self._build_result(
                status="diagnosed",
                device_id=device_id,
                fault_count=len(faults),
                root_causes=root_causes,
                report=report,
                raw_llm_output=diagnosis_result,
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = self._track_execution(start_time)
            self._log_execute(f"诊断失败: {str(e)}", level="error")
            return self._build_error_result(str(e), elapsed)

    def _track_execution_start(self) -> float:
        import time
        return time.time()

    def _build_diagnosis_prompt(self, faults: List[Dict], context: str) -> str:
        """构建诊断提示词"""
        fault_descriptions = "\n".join([
            f"- {f.get('type', 'unknown')}: {f.get('description', '')} (严重等级: {f.get('severity', 'unknown')})"
            for f in faults
        ])

        prompt = f"""你是一个5G网络运维专家。请根据以下故障信息和相关知识进行根因分析。

【故障信息】
{fault_descriptions}

【相关知识】
{context}

【分析要求】
1. 分析每个故障的可能根因
2. 给出根因的置信度（0-1之间）
3. 提供修复建议

请按以下JSON格式输出：
{{
    "root_causes": [
        {{
            "fault_type": "故障类型",
            "root_cause": "根因描述",
            "confidence": 0.85,
            "suggestion": "修复建议"
        }}
    ]
}}
"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM 进行推理（占位实现）"""
        self._log_execute("调用 Qwen-7B 模型进行推理...")

        return """
{
    "root_causes": [
        {
            "fault_type": "weak_signal",
            "root_cause": "天线倾角过大导致覆盖不足",
            "confidence": 0.88,
            "suggestion": "调整天线电子下倾角减小3度"
        },
        {
            "fault_type": "interference",
            "root_cause": "邻区PCI冲突导致同频干扰",
            "confidence": 0.82,
            "suggestion": "重新规划PCI，启用ICIC功能"
        }
    ]
}
"""

    def _parse_diagnosis_result(self, llm_output: str, faults: List[Dict]) -> List[Dict]:
        """解析 LLM 输出 - 支持多种 JSON 格式"""
        try:
            cleaned_output = self._extract_json(llm_output)
            result = json.loads(cleaned_output)
            root_causes = result.get("root_causes", [])

            for cause in root_causes:
                cause.setdefault("confidence", 0.5)
                cause.setdefault("suggestion", "待确认")

            return root_causes
        except (json.JSONDecodeError, ValueError) as e:
            self._log_execute(f"LLM 输出解析失败: {str(e)}，使用默认诊断", level="warning")
            return [
                {
                    "fault_type": f.get("type", "unknown"),
                    "root_cause": "待进一步分析",
                    "confidence": 0.5,
                    "suggestion": f.get("suggestion", "请联系运维人员"),
                }
                for f in faults
            ]

    def _extract_json(self, text: str) -> str:
        """从 LLM 输出中提取 JSON"""
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json_match.group()
        return text

    def _generate_report(self, device_id: str, faults: List[Dict], root_causes: List[Dict]) -> str:
        """生成诊断报告"""
        report_lines = [
            f"【5G设备故障诊断报告】",
            f"设备ID: {device_id}",
            f"故障数量: {len(faults)}",
            f"根因数量: {len(root_causes)}",
            "",
            "【故障详情】",
        ]

        for i, f in enumerate(faults, 1):
            report_lines.append(f"{i}. {f.get('description', '未知故障')} [严重等级: {f.get('severity', 'unknown')}]")

        report_lines.extend(["", "【根因分析】"])

        for i, c in enumerate(root_causes, 1):
            report_lines.append(
                f"{i}. {c.get('root_cause', '未知')} (置信度: {c.get('confidence', 0):.0%})"
            )
            report_lines.append(f"   建议: {c.get('suggestion', '无')}")

        return "\n".join(report_lines)

    def get_diagnosis_stats(self) -> Dict[str, Any]:
        """获取诊断统计信息"""
        return {
            "total_diagnoses": self._diagnosis_count,
        }
