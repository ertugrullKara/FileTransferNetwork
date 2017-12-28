mkdir res/loss_10_udp
mkdir res/loss_10_sctp

for i in {1..2};
do
	python udp_client.py input.txt 1 > res/loss_10_udp/loss_10_udp_exp1_"${i}".txt
	echo "udp exp1 $i done"
done

for i in {1..2};
do
	python udp_client.py input.txt 2 > res/loss_10_udp/loss_10_udp_exp2_"${i}".txt
	echo "udp exp2 $i done"
done

for i in {1..2};
do
	python sctp_client.py input.txt 1 > res/loss_10_sctp/loss_10_sctp_exp1_"${i}".txt
	echo "sctp exp1 $i done"
done
for i in {1..2};
do
	python sctp_client.py input.txt 2 > res/loss_10_sctp/loss_10_sctp_exp2_"${i}".txt
	echo "sctp exp2 $i done"
done
