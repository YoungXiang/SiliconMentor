from DrissionPage import Chromium
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time
import logging

# --------------------- 日志配置 ---------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    filename='jd_buyer.log',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# --------------------- 全局配置 ---------------------
SKU_CONFIG = [
    {
        "sku_id": "10076827331769",
        "buy_time": "2025-2-11 21:56:10",
        "area_id": "19_1607_40152_47419",
        "retry_max": 5
    }
]

COMMON_CONFIG = {
    "buy_btn_text": ["立即购买","在线支付"],
    'debug_port': 9230,
    'max_workers': 2  # 最大并发任务数
}
# ---------------------------------------------------

class JDMissionExecutor:
    def __init__(self):
        self.browser = Chromium(COMMON_CONFIG['debug_port'])
        self.main_tab = self.browser.latest_tab
        self.main_tab.set.window.size(1200, 800)
        #self.main_tab.set.user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    def login(self):
        """登录京东"""
        try:
            self.main_tab.get('https://plogin.m.jd.com/login/login?appid=300&returnurl=https%3A%2F%2Fmy.m.jd.com%2F')
            logger.info("请登录...")
            
            # 等待登录完成
            self.main_tab.wait.url_change('https://my.m.jd.com/', timeout=120)
            logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return False

    def _get_trade_url(self, productId):
        return f"https://trade.m.jd.com/pay?sceneval=2&scene=jd&isCanEdit=1&EncryptInfo=&Token=&bid=&type=0&lg=0&supm=0&wdref=https%3A%2F%2Fitem.m.jd.com%2Fproduct%{productId}.html%3Fsceneval%3D2%26jxsid%3D17291551552449629789%26appCode%3Dms0ca95114%26_fd%3Djdm&commlist={productId},,1,{productId},1,0,0&locationid=1-72-2819-0&jxsid=17291551552449629789&appCode=ms0ca95114#/index"
        
    def _execute_single_mission(self, mission: dict):
        """执行单个商品抢购"""
        tab = self.browser.new_tab()
        try:
            logger.info(f"开始处理商品 {mission['sku_id']}")
            
            # 跳转到商品页
            sku_url = self._get_trade_url(mission['sku_id']) #f"https://item.jd.com/{mission['sku_id']}.html?area={mission['area_id']}"
            logger.info(f"{mission['sku_id']} 正在打开商品页 {sku_url}")

            tab.get(sku_url)
            
            # https://trade.jd.com/shopping/order/getOrderInfo.action?source=common
            # 时间同步等待
            target_time = datetime.strptime(mission['buy_time'], '%Y-%m-%d %H:%M:%S')
            while (delta := (target_time - datetime.now()).total_seconds()) > 0:
                logger.debug(f"{mission['sku_id']} 剩余等待时间: {delta:.1f}s")
                time.sleep(min(0.1, delta))
            
            # 抢购尝试
            success = False
            for attempt in range(mission['retry_max']):
                try:
                    tab.refresh()
                    if tab.ele('无货',timeout=0.1):
                        tab.refresh()

                    for text in COMMON_CONFIG['buy_btn_text']:
                        if buy_btn := tab.ele(f'text:{text}'):
                            buy_btn.click()
                            logger.info(f"{mission['sku_id']} 点击购买成功")
                            success = True
                            tab.wait(0.11, 0.23)
                            return True
                
                except Exception as e:
                    logger.warning(f"{mission['sku_id']} 第{attempt+1}次尝试失败: {str(e)}")
                    time.sleep(0.5)
            
            return False
        finally:
            tab.close()

    def schedule_missions(self):
        """调度所有任务"""
        with ThreadPoolExecutor(max_workers=COMMON_CONFIG['max_workers']) as executor:
            futures = []
            for mission in SKU_CONFIG:
                # 计算任务延迟
                target_time = datetime.strptime(mission['buy_time'], '%Y-%m-%d %H:%M:%S')
                delay = (target_time - datetime.now()).total_seconds()
                
                if delay > 0:
                    logger.info(f"任务 {mission['sku_id']} 计划于 {target_time} 执行")
                    futures.append(executor.submit(self._delayed_execution, mission, delay))
                else:
                    logger.warning(f"跳过过期任务 {mission['sku_id']}")

            # 处理结果
            for future in futures:
                sku_id = future.result()[0]
                status = future.result()[1]
                logger.info(f"任务 {sku_id} {'成功' if status else '失败'}")

    def _delayed_execution(self, mission: dict, delay: float):
        """延迟执行包装器"""
        time.sleep(max(0, delay))
        status = self._execute_single_mission(mission)
        return (mission['sku_id'], status)

if __name__ == '__main__':
    executor = JDMissionExecutor()
    try:
        if executor.login():
            executor.schedule_missions()
        else:
            logger.error("登录失败，程序终止")
    except KeyboardInterrupt:
        logger.info("用户中断执行")
    finally:
        executor.browser.quit()
