import os
import subprocess
import argparse
import sys
import platform
import time
import logging
from datetime import datetime
from pathlib import Path

# 日志配置
class RealTimeFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"本地执行脚本_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        RealTimeFileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = "sk-10e7990a0c9f47518846439e8e0dc67b"
TUSHARE_TOKEN = "3664fe220cb675ae1661e7ad96c51e2592a0ef72c93d29da3d65b692"

TASKS = {
    "anime_js": {"name": "动漫_金山文档推送", "scripts": ["动漫_金山文档推送.py"], "schedule": "每20分钟 (10:08-20:48)"},
    "anime_yt": {"name": "动漫_YouTube推送", "scripts": ["动漫_YouTube推送.py"], "schedule": "每20分钟 (10:08-20:48)"},
    "futures_oil": {"name": "期货_油脂分析", "scripts": ["期货_油脂分析.py"], "schedule": "08:50, 15:32, 21:03, 23:05 (北京时间)"},
    "a_stock_breadth": {"name": "A股_市场宽度报告", "scripts": ["A股_市场宽度报告.py"], "schedule": "17:36 (北京时间)"},
    "a_stock_rotation": {"name": "A股_行业轮动分析", "scripts": ["A股_行业轮动分析.py"], "schedule": "15:41 (北京时间)"},
    "a_stock_limit": {"name": "A股_涨跌停分析", "scripts": ["A股_涨跌停分析.py"], "schedule": "15:41 (北京时间)"},
    "etf_momentum": {"name": "ETF_动量轮动策略", "scripts": ["ETF_动量轮动策略.py"], "schedule": "09:18, 15:23 (北京时间)"},
    "etf_momentum_v2": {"name": "ETF_动量轮动_v295", "scripts": ["ETF_动量轮动_v295.py"], "schedule": "09:18, 15:23 (北京时间)"},
    "etf_ths": {"name": "ETF_同花顺数据分析", "scripts": ["ETF_同花顺数据分析.py"], "schedule": "15:45 (北京时间)"},
}

MODE_1_SCRIPTS = list(TASKS.keys())

MODE_2_SCHEDULES = {
    "futures_oil": ["09:03", "15:05", "21:03", "23:05"],
    "a_stock_breadth": ["17:35"],
    "a_stock_rotation": ["15:05"],
    "a_stock_limit": ["15:05"],
    "etf_momentum": ["09:28", "15:05"],
    "etf_momentum_v2": ["09:28", "15:05"],
    "etf_ths": ["15:05"],
    "anime_js": ["10:08", "10:28", "10:48", "11:08", "11:28", "11:48", "12:08", "12:28", "12:48",
                 "13:08", "13:28", "13:48", "14:08", "14:28", "14:48", "15:08", "15:28", "15:48",
                 "16:08", "16:28", "16:48", "17:08", "17:28", "17:48", "18:08", "18:28", "18:48",
                 "19:08", "19:28", "19:48", "20:08", "20:28", "20:48"],
}

def set_beijing_time():
    os.environ["TZ"] = "Asia/Shanghai"
    print("✅ 已设置时区为北京时间 (Asia/Shanghai)")
    logger.info("已设置时区为北京时间 (Asia/Shanghai)")

def run_script(script_name, env_vars):
    print(f"\n{'='*60}")
    print(f"正在执行: {script_name}")
    print('='*60)
    logger.info(f"="*60)
    logger.info(f"正在执行: {script_name}")
    logger.info(f"="*60)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    try:
        env = os.environ.copy()
        env.update(env_vars)
        result = subprocess.run(
            [sys.executable, script_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=script_dir
        )
        if result.stdout:
            print("标准输出:")
            print(result.stdout)
            logger.info(f"{script_name} 标准输出:\n{result.stdout}")
        if result.stderr:
            print("标准错误:")
            print(result.stderr)
            logger.warning(f"{script_name} 标准错误:\n{result.stderr}")
        if result.returncode == 0:
            print(f"\n✅ {script_name} 执行成功")
            logger.info(f"{script_name} 执行成功")
            return True
        else:
            print(f"\n❌ {script_name} 执行失败，返回码: {result.returncode}")
            logger.error(f"{script_name} 执行失败，返回码: {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        print(f"\n⏱️ {script_name} 执行超时")
        logger.error(f"{script_name} 执行超时")
        return False
    except Exception as e:
        print(f"\n❌ {script_name} 执行异常: {str(e)}")
        logger.error(f"{script_name} 执行异常: {str(e)}")
        return False

def mode1_immediate(env_vars):
    print("\n" + "="*60)
    print("模式1: 立即执行所有脚本")
    print("="*60)
    logger.info("="*60)
    logger.info("模式1: 立即执行所有脚本")
    logger.info("="*60)
    success_count = 0
    total_count = len(MODE_1_SCRIPTS)
    for task_id in MODE_1_SCRIPTS:
        task = TASKS[task_id]
        for script in task["scripts"]:
            if run_script(script, env_vars):
                success_count += 1
    print(f"\n{'='*60}")
    print(f"📊 执行结果: {success_count}/{total_count} 成功")
    logger.info("="*60)
    logger.info(f"📊 执行结果: {success_count}/{total_count} 成功")
    return success_count == total_count

def get_next_run_time(schedules):
    from datetime import datetime
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    for schedule in sorted(schedules):
        if schedule > current_time_str:
            return schedule
    return None

def mode2_schedule(env_vars):
    print("\n" + "="*60)
    print("模式2: 按照定时任务执行 (持续运行)")
    print("="*60)
    logger.info("="*60)
    logger.info("模式2: 按照定时任务执行 (持续运行)")
    logger.info("="*60)

    all_schedules = []
    for task_id, schedules in MODE_2_SCHEDULES.items():
        for s in schedules:
            all_schedules.append((s, task_id))
    all_schedules.sort(key=lambda x: x[0])
    unique_times = sorted(set(s[0] for s in all_schedules))

    print("\n📋 完整定时任务列表:")
    print("-"*60)
    logger.info("完整定时任务列表:")
    for t in unique_times:
        tasks_at_time = [TASKS[tid]["name"] for st, tid in all_schedules if st == t]
        print(f"  🕐 {t} → {', '.join(tasks_at_time)}")
        logger.info(f"  {t} → {', '.join(tasks_at_time)}")

    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def get_all_tasks_at_time(target_time):
        return [tid for st, tid in all_schedules if st == target_time]

    executed_today = set()

    while True:
        now = datetime.now()
        weekday = now.weekday()
        current_time_str = now.strftime("%H:%M")

        if weekday >= 5:
            available_times = [t for t in unique_times if any(tid.startswith("anime") for st, tid in all_schedules if st == t)]
        else:
            available_times = unique_times[:]

        pending_times = [t for t in available_times if t not in executed_today]

        if not pending_times:
            print("\n⚠️  今天没有可执行的任务 (周末或已过最后时间)")
            logger.warning("今天没有可执行的任务 (周末或已过最后时间)")
            print("按回车返回主菜单, q退出程序")
            user_input = input().strip()
            if user_input.lower() == "q":
                break
            return True

        next_time = get_next_run_time(pending_times)

        if next_time is None:
            print("\n" + "="*60)
            print("✅ 今天所有任务已执行完毕!")
            print(f"📅 下一轮任务: 明天 {unique_times[0]}")
            logger.info("="*60)
            logger.info("今天所有任务已执行完毕!")
            logger.info(f"下一轮任务: 明天 {unique_times[0]}")
            print("按回车返回主菜单, q退出程序")
            user_input = input().strip()
            if user_input.lower() == "q":
                break
            return True

        tasks_to_run = get_all_tasks_at_time(next_time)
        executed_today.add(next_time)

        print(f"\n{'='*60}")
        print(f"📅 今天是: {weekday_names[weekday]} {now.strftime('%Y-%m-%d')}")
        print(f"⏰ 当前时间: {current_time_str} (北京时间)")
        print(f"▶️  下次任务时间: {next_time}")
        print(f"📌 待执行任务:")
        for tid in tasks_to_run:
            print(f"     - {TASKS[tid]['name']}")
        logger.info("="*60)
        logger.info(f"今天是: {weekday_names[weekday]} {now.strftime('%Y-%m-%d')}")
        logger.info(f"当前时间: {current_time_str} (北京时间)")
        logger.info(f"下次任务时间: {next_time}")
        logger.info(f"待执行任务:")
        for tid in tasks_to_run:
            logger.info(f"     - {TASKS[tid]['name']}")

        if weekday >= 5:
            print("\n⚠️  提示: 今天是周末，A股/期货任务不运行")
            logger.warning("今天是周末，A股/期货任务不运行")

        target_hour, target_minute = map(int, next_time.split(":"))
        print(f"\n⏳ 距离下次任务还有...")
        logger.info("距离下次任务还有...")

        while True:
            now = datetime.now()
            current_str = now.strftime("%H:%M")
            if current_str >= next_time:
                print(f"\n⏰ 已到达任务时间 {next_time}，开始执行!")
                break
            target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            if target < now:
                target = target.replace(day=target.day + 1)
            diff = target - now
            hours, remainder = divmod(int(diff.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            countdown_str = f"\r   倒计时: {hours:02d}:{minutes:02d}:{seconds:02d}  (回车立即执行, q退出程序)  "
            print(countdown_str, end="", flush=True)
            logger.debug(f"倒计时: {hours:02d}:{minutes:02d}:{seconds:02d}")
            try:
                if sys.stdin.isatty():
                    import select
                    if select.select([sys.stdin], [], [], 1)[0]:
                        user_input = sys.stdin.readline().strip()
                        if user_input.lower() == "q":
                            print("\n\n已退出定时执行")
                            logger.info("用户退出定时执行")
                            return True
                        else:
                            print(f"\n\n⏰ 立即执行任务!")
                            logger.info("用户选择立即执行任务")
                            break
                else:
                    time.sleep(1)
            except:
                time.sleep(1)

        print("\n正在执行...")
        logger.info("开始执行任务")
        success_count = 0
        for task_id in tasks_to_run:
            task = TASKS[task_id]
            for script in task["scripts"]:
                if run_script(script, env_vars):
                    success_count += 1
        print(f"\n📊 执行结果: {success_count}/{len(tasks_to_run)} 成功")
        logger.info(f"本轮执行结果: {success_count}/{len(tasks_to_run)} 成功")

        print("\n" + "="*60)
        print("✅ 本轮任务执行完毕，继续等待下一轮...")
        logger.info("本轮任务执行完毕，继续等待下一轮")
        time.sleep(2)
    return success_count == len(tasks_to_run)

def mode3_specific(task_id, env_vars):
    print("\n" + "="*60)
    print(f"模式3: 执行指定任务 - {TASKS[task_id]['name']}")
    print(f"定时: {TASKS[task_id]['schedule']}")
    print("="*60)
    logger.info("="*60)
    logger.info(f"模式3: 执行指定任务 - {TASKS[task_id]['name']}")
    logger.info(f"定时: {TASKS[task_id]['schedule']}")
    success_count = 0
    task = TASKS[task_id]
    for script in task["scripts"]:
        if run_script(script, env_vars):
            success_count += 1
    print(f"\n{'='*60}")
    print(f"📊 执行结果: {success_count}/{len(task['scripts'])} 成功")
    logger.info("="*60)
    logger.info(f"📊 执行结果: {success_count}/{len(task['scripts'])} 成功")
    return success_count == len(task['scripts'])

def show_menu():
    print("\n" + "="*60)
    print("请选择执行模式:")
    print("="*60)
    print("  1. 立即执行 - 执行所有脚本")
    print("  2. 定时执行 - 按照workflow定时规则执行")
    print("  3. 指定任务 - 选择单个任务执行")
    print("  0. 退出")
    print("="*60)
    logger.info("显示主菜单")

def show_task_menu():
    print("\n" + "="*60)
    print("请选择要执行的任务:")
    print("="*60)
    for i, task_id in enumerate(TASKS.keys(), 1):
        task = TASKS[task_id]
        print(f"  {i}. {task['name']} - {task['schedule']}")
    print(f"  0. 返回上级菜单")
    print("="*60)

def main():
    set_beijing_time()
    env_vars = {
        "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
        "TUSHARE_TOKEN": TUSHARE_TOKEN
    }
    while True:
        show_menu()
        choice = input("请输入选项: ").strip()
        if choice == "1":
            mode1_immediate(env_vars)
        elif choice == "2":
            mode2_schedule(env_vars)
        elif choice == "3":
            while True:
                show_task_menu()
                task_choice = input("请输入选项: ").strip()
                if task_choice == "0":
                    break
                try:
                    idx = int(task_choice) - 1
                    task_ids = list(TASKS.keys())
                    if 0 <= idx < len(task_ids):
                        mode3_specific(task_ids[idx], env_vars)
                    else:
                        print("无效的选项")
                except ValueError:
                    print("请输入有效的数字")
        elif choice == "0":
            print("退出程序")
            break
        else:
            print("无效的选项，请重新选择")

if __name__ == "__main__":
    main()