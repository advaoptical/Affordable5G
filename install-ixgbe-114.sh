#!/bin/bash
set +x #echo on
pushd .
kernel_ver=$(uname -r)

cd /tmp
wget http://10.52.147.132/packages/usr/lib/modules/$kernel_ver/extra/114/ixgbe-5.5.5/ixgbe.ko

if [ $? -ne 0 ]; then
	echo "can't wget ixgbe"
    popd
	exit -1
fi

cd /lib/modules/$kernel_ver/kernel/drivers/net/ethernet/intel/ixgbe/
if [ $? -ne 0 ]; then
	echo "can't find /lib/modules/$kernel_ver/kernel/drivers/net/ethernet/intel/ixgbe/"
    popd
	exit -1
fi

mv /tmp/ixgbe.ko .
rmmod ixgbe
rm -f ixgbe*.*
depmod
dracut -f
popd
echo 'Done'