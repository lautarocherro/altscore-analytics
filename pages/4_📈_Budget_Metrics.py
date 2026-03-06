"""Page wrapper — Budget Metrics analysis"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.budget_metrics import main
main()
